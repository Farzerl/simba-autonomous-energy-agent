from __future__ import annotations

import copy
import hashlib
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping

from src.agent.models import ApprovalDecision, ApprovalLimits, MissionCreateRequest, MissionGoal, MissionState
from src.agent.providers import AgentProvider, build_provider
from src.agent.safety import EnergySafetyFirewall
from src.agent.tools import registry_snapshot
from src.control.actuation_service import ActuationService
from src.control.gateway import ControlGateway
from src.tariff.zetdc_tou import ENERGY_RATES_USD_PER_KWH, classify_tariff_period


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


class AgentService:
    """Persistent, approval-gated, software-only autonomous mission controller."""

    TRANSITIONS: dict[str, set[str]] = {
        MissionState.CREATED: {MissionState.OBSERVING, MissionState.CANCELLED},
        MissionState.OBSERVING: {MissionState.RISK_DETECTED, MissionState.TARGET_MET, MissionState.FAILED},
        MissionState.RISK_DETECTED: {MissionState.PLANNING, MissionState.FAILED},
        MissionState.PLANNING: {MissionState.PLAN_READY, MissionState.FAILED},
        MissionState.PLAN_READY: {MissionState.AWAITING_APPROVAL, MissionState.APPROVED, MissionState.FAILED},
        MissionState.AWAITING_APPROVAL: {MissionState.APPROVED, MissionState.PLANNING, MissionState.REJECTED, MissionState.CANCELLED},
        MissionState.APPROVED: {MissionState.EXECUTING, MissionState.FAILED},
        MissionState.EXECUTING: {MissionState.OBSERVING_RESPONSE, MissionState.FAILED},
        MissionState.OBSERVING_RESPONSE: {MissionState.REPLANNING, MissionState.TARGET_MET, MissionState.FAILED},
        MissionState.REPLANNING: {MissionState.PLAN_READY, MissionState.FAILED},
        MissionState.TARGET_MET: {MissionState.CLOSED},
        MissionState.FAILED: {MissionState.CLOSED},
        MissionState.REJECTED: {MissionState.CLOSED},
        MissionState.CANCELLED: {MissionState.CLOSED},
        MissionState.CLOSED: set(),
    }

    def __init__(
        self,
        project_root: Path,
        *,
        runtime_dir: Path | None = None,
        energy_state_provider: Callable[[], Mapping[str, Any]] | None = None,
        actuation_service: ActuationService | None = None,
        control_gateway: ControlGateway | None = None,
        provider: AgentProvider | None = None,
        config_path: Path | None = None,
        scenarios_path: Path | None = None,
    ) -> None:
        self.root = Path(project_root).resolve()
        self.runtime_dir = Path(runtime_dir or self.root / "runtime" / "agent")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.runtime_dir / "missions.json"
        self.audit_path = self.runtime_dir / "events.jsonl"
        self.config_path = Path(config_path or self.root / "config" / "autonomous_agent.json")
        self.scenarios_path = Path(scenarios_path or self.root / "data" / "simulation" / "scenarios.json")
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.scenario_document = json.loads(self.scenarios_path.read_text(encoding="utf-8"))
        self.energy_state_provider = energy_state_provider
        self.actuation = actuation_service or ActuationService(self.root)
        self.control_gateway = control_gateway or ControlGateway(mode="simulation", allow_live=False)
        self.provider = provider or build_provider(dict(self.config.get("provider") or {}), self.runtime_dir)
        self.firewall = EnergySafetyFirewall()
        self._lock = RLock()
        self._missions = self._load_missions()

    def _load_missions(self) -> dict[str, dict[str, Any]]:
        if not self.store_path.exists():
            return {}
        try:
            value = json.loads(self.store_path.read_text(encoding="utf-8"))
            missions = value.get("missions", {}) if isinstance(value, dict) else {}
            return missions if isinstance(missions, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        _atomic_json(
            self.store_path,
            {
                "schema_version": 1,
                "updated_utc": _utc_now(),
                "mode": "software_in_the_loop",
                "live_control_enabled": False,
                "missions": self._missions,
            },
        )

    def _event(
        self,
        mission: dict[str, Any],
        event_type: str,
        details: Mapping[str, Any] | None = None,
        *,
        from_state: str | None = None,
        to_state: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"evt-{uuid.uuid4().hex[:16]}",
            "sequence": len(mission["events"]) + 1,
            "mission_id": mission["mission_id"],
            "timestamp_utc": _utc_now(),
            "event_type": event_type,
            "from_state": from_state,
            "to_state": to_state or mission["state"],
            "details": copy.deepcopy(dict(details or {})),
        }
        mission["events"].append(event)
        mission["updated_utc"] = event["timestamp_utc"]
        _append_jsonl(self.audit_path, event)
        return event

    def _transition(self, mission: dict[str, Any], state: MissionState, event_type: str, details: Mapping[str, Any] | None = None) -> None:
        current = str(mission["state"])
        target = str(state)
        if target not in {str(item) for item in self.TRANSITIONS.get(current, set())}:
            raise RuntimeError(f"Invalid mission transition {current} -> {target}.")
        mission["state"] = target
        self._event(mission, event_type, details, from_state=current, to_state=target)

    def _scenario(self, scenario_id: str) -> dict[str, Any]:
        for item in list(self.scenario_document.get("scenarios") or []):
            if str(item.get("scenario_id")) == scenario_id:
                return copy.deepcopy(item)
        raise ValueError(f"Unknown simulation scenario '{scenario_id}'.")

    @staticmethod
    def _parse_time(value: object) -> datetime:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _default_goal(self, scenario: Mapping[str, Any]) -> MissionGoal:
        demo = dict(self.config.get("demo") or {})
        start = str(demo.get("target_window_start") or scenario.get("start_time"))
        end = str(demo.get("target_window_end") or (self._parse_time(start) + timedelta(hours=2)).isoformat())
        return MissionGoal(
            peak_limit_kva=float(demo.get("peak_limit_kva") or scenario.get("campus_limit_kva")),
            target_window_start=start,
            target_window_end=end,
            reserve_margin_kva=float(demo.get("reserve_margin_kva", 8.0)),
        )

    def _chronos_status(self) -> dict[str, Any]:
        routing_path = self.root / "models" / "chronos2" / "routing.json"
        setup_path = self.root / "runtime" / "chronos2_setup_state.json"
        known_weight_paths = [
            self.root / "models" / "chronos-2-base" / "model.safetensors",
            self.root / "models" / "chronos-2-finetuned" / "model.safetensors",
            self.root / "models" / "chronos-2-power-quality-finetuned" / "model.safetensors",
        ]
        available_weights = [
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in known_weight_paths
            if path.is_file()
        ]
        result: dict[str, Any] = {
            "available": bool(available_weights),
            "routing_available": routing_path.is_file(),
            "weights_available": bool(available_weights),
            "available_weight_files": available_weights,
            "weights_modified": False,
        }
        if routing_path.exists():
            routing = json.loads(routing_path.read_text(encoding="utf-8"))
            result.update(
                {
                    "eligible": bool(routing.get("eligible")),
                    "deployment_variant": routing.get("deployment_variant"),
                    "selected_by_horizon": {
                        key: dict(value).get("model")
                        for key, value in dict(routing.get("selected_by_horizon") or {}).items()
                    },
                }
            )
        if setup_path.exists():
            setup = json.loads(setup_path.read_text(encoding="utf-8"))
            result["official_base_model_sha256"] = setup.get("official_base_model_sha256")
            result["setup_status"] = setup.get("status")
        if routing_path.exists() and not available_weights:
            result["note"] = (
                "Chronos-2 routing interface metadata is included, but the large forecasting weights "
                "are intentionally excluded from the public ADTC package. The reproducible replay "
                "uses the recorded software-in-the-loop scenario, not Chronos inference."
            )
        return result

    def _live_state(self) -> dict[str, Any]:
        if self.energy_state_provider is None:
            return {"status": "not_connected"}
        try:
            state = dict(self.energy_state_provider())
            if str(state.get("status", "ready")) == "warming":
                return {
                    "status": "warming",
                    "note": "The existing forecast batch has not been cached yet; the mission uses the validated replay fixture and Chronos routing metadata.",
                    "control_gateway": dict(state.get("control_gateway") or {}),
                }
            campus = dict(state.get("campus") or {})
            model = dict(state.get("model") or {})
            return {
                "status": "connected",
                "current_timestamp": state.get("current_timestamp"),
                "campus": {
                    "controlled_kva": campus.get("controlled_kva"),
                    "forecast_kva": campus.get("forecast_kva"),
                    "limit_kva": campus.get("limit_kva"),
                    "risk": campus.get("risk"),
                },
                "forecast_count": len(list(state.get("forecasts") or [])),
                "anomaly_count": len(list(state.get("anomalies") or [])),
                "model_source": model.get("model_type") or model.get("active_model") or model.get("source"),
                "control_gateway": dict(state.get("control_gateway") or {}),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)[:300]}

    def _observation(self, scenario: Mapping[str, Any], goal: MissionGoal) -> dict[str, Any]:
        facilities = list(scenario.get("facilities") or [])
        steps = min(len(list(item.get("baseline_kva") or [])) for item in facilities)
        campus_series = [
            sum(float(list(item.get("baseline_kva") or [])[index]) for item in facilities)
            for index in range(steps)
        ]
        target_index = max(range(len(campus_series)), key=campus_series.__getitem__)
        scenario_start = self._parse_time(scenario.get("start_time"))
        target_timestamp = scenario_start + timedelta(minutes=30 * target_index)
        forecast = max(
            float(scenario.get("observed_peak_kva", 0.0) or 0.0),
            campus_series[target_index],
        )
        facility_rows = [
            {
                "facility_id": str(item.get("facility_id")),
                "facility_name": str(item.get("name")),
                "model_alias": str(item.get("model_alias") or item.get("name")),
                "target_kva": _round(float(list(item.get("baseline_kva") or [])[target_index])),
                "limit_kva": _round(float(item.get("limit_kva", 0.0) or 0.0)),
                "critical_floor_kva": _round(float(item.get("critical_floor_kva", 0.0) or 0.0)),
            }
            for item in facilities
        ]
        period = classify_tariff_period(target_timestamp)
        return {
            "source": "existing_simulator_history_with_live_forecast_adapter",
            "scenario_id": scenario.get("scenario_id"),
            "target_index": target_index,
            "target_timestamp": target_timestamp.isoformat(),
            "campus_forecast_kva": _round(forecast),
            "campus_limit_kva": _round(goal.peak_limit_kva),
            "required_reduction_kva": _round(max(forecast - goal.peak_limit_kva + goal.reserve_margin_kva, 0.0)),
            "tariff_period": period,
            "tariff_rate_usd_per_kwh": ENERGY_RATES_USD_PER_KWH[period],
            "facilities": facility_rows,
            "chronos2": self._chronos_status(),
            "live_runtime": self._live_state(),
            "power_quality_source": "existing_power_quality_forecaster",
            "anomaly_source": "existing_anomaly_logic",
        }

    def _devices_for_facility(self, facility: Mapping[str, Any]) -> list[dict[str, Any]]:
        for name in (
            str(facility.get("name") or ""),
            str(facility.get("model_alias") or ""),
            str(facility.get("facility_id") or ""),
        ):
            if not name:
                continue
            devices = self.actuation.devices(name)
            if devices:
                return devices
        return []

    def _device_lookup(self) -> dict[str, dict[str, Any]]:
        return {str(item.get("device_id")): item for item in self.actuation.devices()}

    def _generate_candidates(
        self,
        mission: Mapping[str, Any],
        scenario: Mapping[str, Any],
        *,
        excluded_candidate_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        excluded = excluded_candidate_ids or set()
        observation = dict(mission["observation"])
        target_index = int(observation["target_index"])
        effects = dict(self.config.get("response_effects") or {})
        goal = dict(mission["goal"])
        scope = {str(item) for item in goal.get("facility_scope", [])}
        target_timestamp = self._parse_time(observation["target_timestamp"])
        # The target timestamp belongs to a historical software replay. Command
        # freshness is therefore anchored to wall-clock approval time, not the
        # replay timestamp, so stale-command protection remains meaningful.
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        candidates: list[dict[str, Any]] = []
        for facility in list(scenario.get("facilities") or []):
            facility_id = str(facility.get("facility_id"))
            facility_name = str(facility.get("name"))
            if scope and facility_id not in scope and facility_name not in scope:
                continue
            devices = self._devices_for_facility(facility)
            by_class = {str(item.get("classification")): item for item in devices if bool(item.get("actuation_allowed"))}
            baseline = float(list(facility.get("baseline_kva") or [])[target_index])
            critical_floor = float(facility.get("critical_floor_kva", 0.0) or 0.0)
            for group in sorted(list(facility.get("load_groups") or []), key=lambda item: int(item.get("priority", 99) or 99)):
                classification = str(group.get("classification", "critical"))
                if classification not in {"deferrable", "sheddable"}:
                    continue
                candidate_id = f"{facility_id}:{group.get('load_group_id')}"
                if candidate_id in excluded:
                    continue
                maximum = max(
                    float(group.get("rated_kva", 0.0) or 0.0)
                    * (1.0 - float(group.get("minimum_service_fraction", 1.0) or 0.0)),
                    0.0,
                )
                if maximum <= 0:
                    continue
                factors = dict(effects.get(classification) or {})
                expected_factor = float(factors.get("expected_factor", 0.85))
                confidence = float(factors.get("confidence", 0.85))
                device = by_class.get(classification)
                priority = int(group.get("priority", 99) or 99)
                action = {
                    "candidate_id": candidate_id,
                    "facility_id": facility_id,
                    "facility_name": facility_name,
                    "facility_model_alias": str(facility.get("model_alias") or facility_name),
                    "load_group": str(group.get("load_group_id")),
                    "load_group_name": str(group.get("name")),
                    "classification": classification,
                    "critical_load": False,
                    "action": "defer_load" if classification == "deferrable" else "shed_load",
                    "maximum_available_kva": _round(maximum),
                    "reduction_kva": _round(maximum),
                    "expected_response_kva": _round(maximum * expected_factor),
                    "response_factor": expected_factor,
                    "confidence": confidence,
                    "duration_minutes": min(int(group.get("max_duration_minutes", 30) or 30), 60 if classification == "deferrable" else 30),
                    "priority": priority,
                    "disruption_score": _round(min(0.15 + priority * 0.08 + (0.18 if classification == "sheddable" else 0.0), 1.0)),
                    "facility_target_kva": _round(baseline),
                    "critical_floor_kva": _round(critical_floor),
                    "projected_facility_kva": _round(baseline - maximum),
                    "device_id": str((device or {}).get("device_id") or ""),
                    "device_family": str((device or {}).get("product_family") or ""),
                    "control_mode": "hardware_emulation",
                    "live_control_enabled": False,
                    "starts_at": target_timestamp.isoformat(),
                    "expires_at": expires_at,
                }
                check = self.firewall.check_action(
                    action,
                    device=device,
                    approval_status="planning",
                    require_approval=False,
                )
                action["planning_safety"] = check.as_dict()
                if check.allowed:
                    candidates.append(action)
        candidates.sort(
            key=lambda item: (
                float(item["expected_response_kva"]) * float(item["confidence"]) / (1.0 + float(item["disruption_score"])),
                -int(item["priority"]),
            ),
            reverse=True,
        )
        return candidates[: int(dict(self.config.get("context") or {}).get("max_candidates", 32))]

    @staticmethod
    def _trim_action(action: Mapping[str, Any], remaining_effect_kva: float) -> dict[str, Any]:
        selected = copy.deepcopy(dict(action))
        factor = max(float(selected.get("response_factor", 0.85) or 0.85), 0.05)
        reduction = min(float(selected["maximum_available_kva"]), remaining_effect_kva / factor)
        selected["reduction_kva"] = _round(reduction)
        selected["expected_response_kva"] = _round(reduction * factor)
        selected["projected_facility_kva"] = _round(float(selected["facility_target_kva"]) - reduction)
        return selected

    def _generate_plans(
        self,
        mission: Mapping[str, Any],
        candidates: list[Mapping[str, Any]],
        required_reduction_kva: float,
        *,
        plan_version: int,
        limits: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        constraints = dict(limits or {})
        weights = dict(self.config.get("planning_weights") or {})
        tariff_rate = float(dict(mission["observation"]).get("tariff_rate_usd_per_kwh", 0.0) or 0.0)
        strategies = {
            "balanced": lambda item: (
                float(item["expected_response_kva"]) * float(item["confidence"]) / (1.0 + float(item["disruption_score"])),
                -int(item["priority"]),
            ),
            "least_disruption": lambda item: (-float(item["disruption_score"]), float(item["expected_response_kva"])),
            "highest_confidence": lambda item: (float(item["confidence"]), float(item["expected_response_kva"])),
        }
        device_lookup = self._device_lookup()
        results: list[dict[str, Any]] = []
        signatures: set[tuple[str, ...]] = set()
        for strategy, key in strategies.items():
            remaining = max(required_reduction_kva, 0.0)
            actions: list[dict[str, Any]] = []
            for item in sorted(candidates, key=key, reverse=True):
                if remaining <= 0.001:
                    break
                selected = self._trim_action(item, remaining)
                actions.append(selected)
                remaining -= float(selected["expected_response_kva"])
            signature = tuple(str(item["candidate_id"]) for item in actions)
            if not actions or signature in signatures:
                continue
            signatures.add(signature)
            safety = self.firewall.check_plan(
                actions,
                device_lookup=device_lookup,
                approval_status="planning",
                limits=constraints,
                require_approval=False,
            )
            if not safety["allowed"]:
                continue
            expected = sum(float(item["expected_response_kva"]) for item in actions)
            confidence = sum(float(item["confidence"]) for item in actions) / len(actions)
            disruption = sum(float(item["disruption_score"]) for item in actions) / len(actions)
            savings = sum(
                float(item["expected_response_kva"]) * float(item["duration_minutes"]) / 60.0 * tariff_rate
                for item in actions
            )
            coverage = min(expected / max(required_reduction_kva, 1e-6), 1.0)
            score = (
                float(weights.get("safety", 0.25))
                + float(weights.get("goal_coverage", 0.35)) * coverage
                + float(weights.get("confidence", 0.15)) * confidence
                + float(weights.get("low_disruption", 0.15)) * (1.0 - disruption)
                + float(weights.get("cost", 0.05)) * min(savings / 25.0, 1.0)
                + float(weights.get("compactness", 0.05)) * (1.0 - min(len(actions) / 12.0, 1.0))
            )
            results.append(
                {
                    "plan_id": f"plan-v{plan_version}-{strategy}",
                    "plan_version": plan_version,
                    "strategy": strategy,
                    "score": _round(score, 5),
                    "required_reduction_kva": _round(required_reduction_kva),
                    "expected_reduction_kva": _round(expected),
                    "remaining_gap_kva": _round(max(required_reduction_kva - expected, 0.0)),
                    "mean_confidence": _round(confidence, 4),
                    "disruption_score": _round(disruption, 4),
                    "estimated_energy_value_usd": _round(savings, 3),
                    "actions": actions,
                    "safety": safety,
                }
            )
        return sorted(results, key=lambda item: float(item["score"]), reverse=True)

    @staticmethod
    def _compact_state(mission: Mapping[str, Any]) -> dict[str, Any]:
        observation = dict(mission["observation"])
        return {
            "mission_id": mission["mission_id"],
            "state": mission["state"],
            "goal": {
                "peak_limit_kva": mission["goal"]["peak_limit_kva"],
                "reserve_margin_kva": mission["goal"]["reserve_margin_kva"],
                "critical_load_policy": "exclude",
            },
            "campus_forecast_kva": observation["campus_forecast_kva"],
            "required_reduction_kva": observation["required_reduction_kva"],
            "tariff_period": observation["tariff_period"],
            "candidate_count": len(list(mission.get("candidates") or [])),
            "live_control_enabled": False,
        }

    def _select_plan(self, mission: dict[str, Any], plans: list[dict[str, Any]]) -> dict[str, Any]:
        if not plans:
            raise ValueError("No safety-cleared plan can satisfy the mission constraints.")
        try:
            selection = self.provider.select_plan(self._compact_state(mission), plans)
        except Exception as exc:
            selection = {
                "selected_plan_id": plans[0]["plan_id"],
                "rationale": "The optional local LLM was unavailable, so deterministic ranking remained authoritative.",
                "provider": "deterministic_fallback",
                "provider_error": str(exc)[:300],
                "llm_calls": 0,
            }
        valid = {str(item["plan_id"]): item for item in plans}
        selected_id = str(selection.get("selected_plan_id"))
        if selected_id not in valid:
            selected_id = str(plans[0]["plan_id"])
            selection["selected_plan_id"] = selected_id
            selection["validation_override"] = "Provider output was outside the deterministic plan set."
        mission["provider_selection"] = selection
        return valid[selected_id]

    def _new_approval(self, mission: Mapping[str, Any], selected: Mapping[str, Any], version: int) -> dict[str, Any]:
        return {
            "approval_id": f"approval-{uuid.uuid4().hex[:16]}",
            "mission_id": mission["mission_id"],
            "plan_id": selected["plan_id"],
            "plan_version": version,
            "status": "pending",
            "allowed_decisions": [item.value for item in ApprovalDecision],
            "actions": copy.deepcopy(list(selected.get("actions") or [])),
            "limits": {},
            "operator": None,
            "decision_note": "",
            "created_utc": _utc_now(),
            "decided_utc": None,
            "safety_boundary": "Critical loads excluded. Live switching disabled. Dynamic replanning may only use safety-cleared actions inside approval limits.",
        }

    def create_mission(self, request: MissionCreateRequest | None = None) -> dict[str, Any]:
        payload = request or MissionCreateRequest()
        with self._lock:
            scenario = self._scenario(payload.scenario_id)
            goal = payload.goal or self._default_goal(scenario)
            mission_id = f"mission-{uuid.uuid4().hex[:16]}"
            mission: dict[str, Any] = {
                "schema_version": 1,
                "mission_id": mission_id,
                "state": str(MissionState.CREATED),
                "objective": goal.objective,
                "goal": goal.model_dump(),
                "scenario_id": payload.scenario_id,
                "demo_mode": bool(payload.demo_mode),
                "complication": str(payload.complication),
                "complication_injected": False,
                "control_boundary": {"mode": "software_in_the_loop", "hardware_emulation": True, "live_control_enabled": False},
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
                "events": [],
                "candidates": [],
                "plans": [],
                "plan_history": [],
                "selected_plan_id": None,
                "approval": None,
                "executions": [],
                "verification": None,
                "metrics": {"replan_count": 0, "llm_calls": 0, "critical_load_actions": 0},
            }
            self._event(mission, "mission_created", {"objective": mission["objective"]}, from_state=None, to_state=str(MissionState.CREATED))
            self._transition(mission, MissionState.OBSERVING, "observation_started")
            mission["observation"] = self._observation(scenario, goal)
            required = float(mission["observation"]["required_reduction_kva"])
            if required <= 0:
                self._transition(mission, MissionState.TARGET_MET, "target_already_met", {"required_reduction_kva": 0.0})
            else:
                self._transition(
                    mission,
                    MissionState.RISK_DETECTED,
                    "peak_risk_detected",
                    {
                        "forecast_kva": mission["observation"]["campus_forecast_kva"],
                        "limit_kva": goal.peak_limit_kva,
                        "required_reduction_kva": required,
                    },
                )
                self._transition(mission, MissionState.PLANNING, "planning_started")
                mission["candidates"] = self._generate_candidates(mission, scenario)
                plans = self._generate_plans(mission, mission["candidates"], required, plan_version=1)
                selected = self._select_plan(mission, plans)
                mission["plans"] = plans
                mission["plan_history"].append(copy.deepcopy(selected))
                mission["selected_plan_id"] = selected["plan_id"]
                mission["metrics"]["llm_calls"] += int(mission["provider_selection"].get("llm_calls", 0) or 0)
                self._transition(
                    mission,
                    MissionState.PLAN_READY,
                    "plan_ranked",
                    {"selected_plan_id": selected["plan_id"], "candidate_count": len(mission["candidates"]), "plan_count": len(plans)},
                )
                mission["approval"] = self._new_approval(mission, selected, 1)
                self._transition(mission, MissionState.AWAITING_APPROVAL, "approval_requested", {"approval_id": mission["approval"]["approval_id"]})
            self._missions[mission_id] = mission
            self._save()
            return copy.deepcopy(mission)

    @staticmethod
    def _selected_plan(mission: Mapping[str, Any]) -> dict[str, Any]:
        selected_id = str(mission.get("selected_plan_id"))
        for item in list(mission.get("plans") or []):
            if str(item.get("plan_id")) == selected_id:
                return copy.deepcopy(item)
        raise ValueError("The selected mission plan is unavailable.")

    def _rebuild_after_modification(self, mission: dict[str, Any], modifications: Mapping[str, Any]) -> None:
        allowed = {"peak_limit_kva", "reserve_margin_kva", "facility_scope", "target_window_start", "target_window_end", "objective"}
        unknown = set(modifications) - allowed
        if unknown:
            raise ValueError(f"Unsupported mission modification(s): {', '.join(sorted(unknown))}.")
        updated_goal = {**dict(mission["goal"]), **{key: value for key, value in modifications.items() if key in allowed}}
        goal = MissionGoal.model_validate(updated_goal)
        mission["goal"] = goal.model_dump()
        mission["objective"] = goal.objective
        self._transition(mission, MissionState.PLANNING, "mission_modified", {"fields": sorted(modifications)})
        scenario = self._scenario(str(mission["scenario_id"]))
        mission["observation"] = self._observation(scenario, goal)
        required = float(mission["observation"]["required_reduction_kva"])
        mission["candidates"] = self._generate_candidates(mission, scenario)
        version = int(dict(mission.get("approval") or {}).get("plan_version", 1)) + 1
        plans = self._generate_plans(mission, mission["candidates"], required, plan_version=version)
        selected = self._select_plan(mission, plans)
        mission["plans"] = plans
        mission["plan_history"].append(copy.deepcopy(selected))
        mission["selected_plan_id"] = selected["plan_id"]
        mission["metrics"]["llm_calls"] += int(mission["provider_selection"].get("llm_calls", 0) or 0)
        self._transition(mission, MissionState.PLAN_READY, "modified_plan_ready", {"selected_plan_id": selected["plan_id"]})
        mission["approval"] = self._new_approval(mission, selected, version)
        self._transition(mission, MissionState.AWAITING_APPROVAL, "approval_requested", {"approval_id": mission["approval"]["approval_id"]})

    def _current_device(self, device_id: str) -> dict[str, Any] | None:
        for item in self.actuation.devices():
            if str(item.get("device_id")) == device_id:
                return item
        return None

    def _approval_defaults(self, mission: Mapping[str, Any]) -> dict[str, Any]:
        planned = self._selected_plan(mission)
        requested = sum(float(item.get("reduction_kva", 0.0) or 0.0) for item in list(planned.get("actions") or []))
        return {
            "max_total_reduction_kva": _round(max(requested * 2.0, requested + 80.0)),
            "max_actions": min(len(list(planned.get("actions") or [])) + 10, 30),
            "permitted_facilities": [],
            "prohibited_load_groups": [],
            "expires_at": None,
            "allow_dynamic_replanning": True,
            "note": "Default software-in-the-loop mission envelope.",
        }

    def decide_mission(
        self,
        mission_id: str,
        decision: ApprovalDecision | str,
        *,
        operator: str,
        limits: ApprovalLimits | Mapping[str, Any] | None = None,
        modifications: Mapping[str, Any] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            mission = self._missions.get(mission_id)
            if mission is None:
                raise KeyError(mission_id)
            if str(mission["state"]) != str(MissionState.AWAITING_APPROVAL):
                raise ValueError("The mission is not awaiting an operator decision.")
            selected_decision = ApprovalDecision(str(decision))
            approval = dict(mission["approval"])
            approval["operator"] = operator
            approval["decision_note"] = note
            approval["decided_utc"] = _utc_now()
            if selected_decision == ApprovalDecision.REJECT:
                approval["status"] = "rejected"
                mission["approval"] = approval
                self._transition(mission, MissionState.REJECTED, "mission_rejected", {"operator": operator, "note": note})
                self._save()
                return copy.deepcopy(mission)
            if selected_decision == ApprovalDecision.MODIFY:
                approval["status"] = "modify_requested"
                mission["approval"] = approval
                self._event(mission, "modification_requested", {"operator": operator, "modifications": dict(modifications or {})})
                self._rebuild_after_modification(mission, dict(modifications or {}))
                self._save()
                return copy.deepcopy(mission)

            selected_limits = self._approval_defaults(mission)
            if limits is not None:
                supplied = limits.model_dump(exclude_none=True) if isinstance(limits, ApprovalLimits) else dict(limits)
                selected_limits.update(supplied)
            approval["status"] = "approved"
            approval["decision"] = selected_decision.value
            approval["limits"] = selected_limits
            approval["dynamic_replanning_authorised"] = bool(selected_limits.get("allow_dynamic_replanning", True))
            mission["approval"] = approval
            plan = self._selected_plan(mission)
            safety = self.firewall.check_plan(
                list(plan.get("actions") or []),
                device_lookup=self._device_lookup(),
                approval_status="approved",
                limits=selected_limits,
            )
            approval["safety_check"] = safety
            mission["approval"] = approval
            if not safety["allowed"]:
                raise ValueError("The approved limits do not permit the selected plan.")
            self._transition(
                mission,
                MissionState.APPROVED,
                "mission_approved",
                {"operator": operator, "decision": selected_decision.value, "limits": selected_limits},
            )
            self._execute_mission(mission, operator)
            self._save()
            return copy.deepcopy(mission)

    def _dispatch_action(self, action: Mapping[str, Any], operator: str, actual_factor: float) -> dict[str, Any]:
        duration = int(action.get("duration_minutes", 30) or 30)
        start = self._parse_time(action.get("starts_at"))
        command = {
            **dict(action),
            "facility_id": str(action.get("facility_model_alias") or action.get("facility_id")),
            "approved_by_operator": True,
            "operator": operator,
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(minutes=duration)).isoformat(),
        }
        acknowledgement = self.control_gateway.dispatch(command)
        realised = float(action.get("reduction_kva", 0.0) or 0.0) * actual_factor
        return {
            "execution_id": f"execution-{uuid.uuid4().hex[:16]}",
            "candidate_id": action.get("candidate_id"),
            "plan_id": action.get("plan_id"),
            "facility_id": action.get("facility_id"),
            "facility_name": action.get("facility_name"),
            "load_group": action.get("load_group"),
            "classification": action.get("classification"),
            "device_id": action.get("device_id"),
            "requested_reduction_kva": action.get("reduction_kva"),
            "expected_reduction_kva": action.get("expected_response_kva"),
            "realised_reduction_kva": _round(realised),
            "status": "simulated_acknowledged",
            "transport": acknowledgement.get("transport"),
            "command_id": acknowledgement.get("command_id"),
            "live_switching": False,
            "timestamp_utc": _utc_now(),
        }

    def _execute_mission(self, mission: dict[str, Any], operator: str) -> None:
        scenario = self._scenario(str(mission["scenario_id"]))
        approval = dict(mission["approval"])
        limits = dict(approval.get("limits") or {})
        excluded: set[str] = set()
        executed: set[str] = set()
        realised_total = sum(float(item.get("realised_reduction_kva", 0.0) or 0.0) for item in mission["executions"])
        initial_forecast = float(mission["observation"]["campus_forecast_kva"])
        target_limit = float(mission["goal"]["peak_limit_kva"])
        reserve = float(mission["goal"].get("reserve_margin_kva", 0.0) or 0.0)
        restored_device: dict[str, Any] | None = None
        attempts = 0
        try:
            while attempts < 3:
                attempts += 1
                plan = self._selected_plan(mission)
                actions = [copy.deepcopy(item) for item in list(plan.get("actions") or [])]
                for action in actions:
                    action["plan_id"] = plan["plan_id"]
                self._transition(mission, MissionState.EXECUTING, "plan_execution_started", {"plan_id": plan["plan_id"], "attempt": attempts})

                if (
                    attempts == 1
                    and str(mission.get("complication")) == "device_unavailable"
                    and not bool(mission.get("complication_injected"))
                    and actions
                ):
                    target_device = self._current_device(str(actions[0].get("device_id")))
                    if target_device:
                        restored_device = copy.deepcopy(target_device)
                        self.actuation.set_emulated_device_state(str(target_device["device_id"]), communication="offline")
                        mission["complication_injected"] = True
                        self._event(
                            mission,
                            "complication_injected",
                            {
                                "type": "device_unavailable",
                                "device_id": target_device["device_id"],
                                "facility": target_device["facility_name"],
                                "effect": "The safety firewall must block this device and trigger replanning.",
                            },
                        )

                successful_this_attempt = 0
                for action in actions:
                    candidate_id = str(action.get("candidate_id"))
                    if candidate_id in executed or candidate_id in excluded:
                        continue
                    device = self._current_device(str(action.get("device_id")))
                    check = self.firewall.check_action(
                        action,
                        device=device,
                        approval_status="approved",
                        limits=limits,
                    )
                    if not check.allowed:
                        excluded.add(candidate_id)
                        self._event(
                            mission,
                            "action_blocked_by_safety_firewall",
                            {"candidate_id": candidate_id, "device_id": action.get("device_id"), "safety": check.as_dict()},
                        )
                        continue
                    factors = dict(dict(self.config.get("response_effects") or {}).get(str(action["classification"])) or {})
                    actual_factor = float(factors.get("actual_factor", action.get("response_factor", 0.8)))
                    if (
                        str(mission.get("complication")) == "underperforming_action"
                        and not bool(mission.get("complication_injected"))
                    ):
                        actual_factor *= float(dict(self.config.get("demo") or {}).get("underperformance_multiplier", 0.45))
                        mission["complication_injected"] = True
                        self._event(
                            mission,
                            "complication_injected",
                            {"type": "underperforming_action", "candidate_id": candidate_id, "actual_factor": actual_factor},
                        )
                    execution = self._dispatch_action(action, operator, actual_factor)
                    mission["executions"].append(execution)
                    realised_total += float(execution["realised_reduction_kva"])
                    executed.add(candidate_id)
                    successful_this_attempt += 1
                    self._event(mission, "emulated_action_executed", execution)

                self._transition(mission, MissionState.OBSERVING_RESPONSE, "response_observation_started", {"attempt": attempts})
                observed = max(initial_forecast - realised_total, 0.0)
                verification = {
                    "attempt": attempts,
                    "baseline_forecast_kva": _round(initial_forecast),
                    "realised_reduction_kva": _round(realised_total),
                    "observed_campus_kva": _round(observed),
                    "target_limit_kva": _round(target_limit),
                    "headroom_kva": _round(target_limit - observed),
                    "target_met": observed <= target_limit + 1e-6,
                    "critical_load_actions": 0,
                    "live_switching": False,
                    "verified_utc": _utc_now(),
                }
                mission["verification"] = verification
                self._event(mission, "impact_verified", verification)
                if verification["target_met"]:
                    self._transition(mission, MissionState.TARGET_MET, "mission_target_met", verification)
                    return
                if not bool(approval.get("dynamic_replanning_authorised")):
                    self._transition(mission, MissionState.FAILED, "replanning_not_authorised", verification)
                    return
                self._transition(
                    mission,
                    MissionState.REPLANNING,
                    "replanning_started",
                    {"observed_campus_kva": observed, "remaining_gap_kva": _round(observed - target_limit)},
                )
                mission["metrics"]["replan_count"] += 1
                required = max(observed - target_limit + reserve, 0.0)
                candidates = self._generate_candidates(mission, scenario, excluded_candidate_ids=excluded | executed)
                plan_version = int(dict(mission["approval"]).get("plan_version", 1)) + int(mission["metrics"]["replan_count"])
                plans = self._generate_plans(
                    mission,
                    candidates,
                    required,
                    plan_version=plan_version,
                    limits=limits,
                )
                if not plans:
                    self._transition(mission, MissionState.FAILED, "no_safe_replan_available", {"remaining_gap_kva": _round(required)})
                    return
                selected = self._select_plan(mission, plans)
                mission["plans"] = plans
                mission["plan_history"].append(copy.deepcopy(selected))
                mission["selected_plan_id"] = selected["plan_id"]
                mission["metrics"]["llm_calls"] += int(mission["provider_selection"].get("llm_calls", 0) or 0)
                self._transition(mission, MissionState.PLAN_READY, "replan_ready", {"selected_plan_id": selected["plan_id"]})
                self._transition(
                    mission,
                    MissionState.APPROVED,
                    "replan_inherited_mission_approval",
                    {"approval_id": approval["approval_id"], "inside_limits": True},
                )
                if successful_this_attempt == 0 and attempts >= 2 and not candidates:
                    self._transition(mission, MissionState.FAILED, "emulated_resources_unavailable")
                    return
            self._transition(mission, MissionState.FAILED, "maximum_replans_exceeded")
        finally:
            if restored_device:
                self.actuation.set_emulated_device_state(
                    str(restored_device["device_id"]),
                    communication=str(restored_device.get("communication") or "online"),
                    control_mode=str(restored_device.get("control_mode") or "remote"),
                    health=str(restored_device.get("health") or "healthy"),
                )
                self._event(
                    mission,
                    "emulated_device_restored",
                    {"device_id": restored_device["device_id"], "communication": restored_device.get("communication")},
                )

    def run_demo(
        self,
        operator: str = "simba-operator",
        *,
        approval_mode: str = "approve_with_limits",
        complication: str = "device_unavailable",
    ) -> dict[str, Any]:
        if complication not in {"device_unavailable", "underperforming_action"}:
            raise ValueError("Unsupported resilience complication.")
        mission = self.create_mission(MissionCreateRequest(demo_mode=True, complication=complication))
        if str(mission["state"]) != str(MissionState.AWAITING_APPROVAL):
            return mission
        decision = ApprovalDecision.APPROVE_WITH_LIMITS if approval_mode == "approve_with_limits" else ApprovalDecision.APPROVE
        limits = ApprovalLimits(
            max_total_reduction_kva=250.0,
            max_actions=20,
            allow_dynamic_replanning=True,
            note="Software-only mission envelope: critical loads excluded.",
        )
        return self.decide_mission(mission["mission_id"], decision, operator=operator, limits=limits)

    def mission(self, mission_id: str) -> dict[str, Any]:
        with self._lock:
            if mission_id not in self._missions:
                raise KeyError(mission_id)
            return copy.deepcopy(self._missions[mission_id])

    def missions(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            items = sorted(self._missions.values(), key=lambda item: str(item.get("created_utc", "")), reverse=True)
            return [copy.deepcopy(item) for item in items[:limit]]

    def status(self) -> dict[str, Any]:
        with self._lock:
            latest = self.missions(1)
            return {
                "status": "ready",
                "mode": "software_in_the_loop",
                "hardware_emulation": True,
                "live_control_enabled": False,
                "facility_count": int(self.scenario_document.get("facility_count", 0) or 0),
                "mission_count": len(self._missions),
                "latest_mission": latest[0] if latest else None,
                "provider": self.provider.status(),
                "control_gateway": self.control_gateway.status(),
                "chronos2": self._chronos_status(),
                "state_model": [item.value for item in MissionState],
                "approval_semantics": [item.value for item in ApprovalDecision],
            }

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        return registry_snapshot()
