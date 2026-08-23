from __future__ import annotations

import json
import math
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping


SOURCE_MODE = "hardware_emulation"
ALLOWED_CLASSIFICATIONS = {"deferrable", "sheddable"}
BLOCKED_CLASSIFICATIONS = {"critical"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _slug(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip()).strip("-").upper()
    return text[:28] or "FACILITY"


def _normalise(value: object) -> str:
    text = str(value or "").lower().replace("&", " and ")
    text = re.sub(r"\band\b", " ", text)
    return re.sub(r"[^a-z0-9]", "", text)


def _atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, row: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


class ActuationService:
    """External control-side hardware emulator for SIMBA-EMS.

    This service intentionally does not operate real electrical equipment. It models the
    control contract that a commissioned breaker/contactor gateway must implement and
    keeps a strict separation between authorised, commanded, device-confirmed and
    meter-verified impact.
    """

    def __init__(
        self,
        project_root: Path,
        *,
        registry_path: Path | None = None,
        state_path: Path | None = None,
        event_log_path: Path | None = None,
        approval_store_path: Path | None = None,
        simulator_state_path: Path | None = None,
        system_settings_path: Path | None = None,
    ) -> None:
        self.root = Path(project_root).resolve()
        self.registry_path = registry_path or self.root / "config" / "actuation_devices.json"
        self.runtime_dir = self.root / "runtime" / "actuation"
        self.state_path = state_path or self.runtime_dir / "state.json"
        self.event_log_path = event_log_path or self.runtime_dir / "events.jsonl"
        self.approval_store_path = approval_store_path or self.root / "runtime" / "workstation_simulator" / "external_approval.json"
        self.simulator_state_path = simulator_state_path or self.root / "runtime" / "workstation_simulator" / "state.json"
        self.system_settings_path = system_settings_path or self.root / "runtime" / "system_settings.json"
        self._lock = RLock()
        self.registry = self._load_registry()
        self.state = self._load_state()
        self._ensure_devices()
        self._save()

    def _load_registry(self) -> dict[str, Any]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if str(payload.get("mode")) != SOURCE_MODE:
            raise RuntimeError("Actuation Center must start in hardware_emulation mode.")
        return payload

    def _load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
        return {
            "schema_version": 2,
            "mode": SOURCE_MODE,
            "created_utc": _iso(),
            "updated_utc": _iso(),
            "devices": {},
            "commands": [],
            "processed_action_keys": [],
            "peak_emulated_reduction_kva": 0.0,
            "last_sync_utc": None,
            "last_simulator_source": None,
        }

    def _save(self) -> None:
        self.state["updated_utc"] = _iso()
        _atomic_json(self.state_path, self.state)

    def _log(self, event: str, **fields: object) -> None:
        _append_jsonl(self.event_log_path, {"timestamp_utc": _iso(), "event": event, **fields})

    def _facility_template(self, facility: str) -> dict[str, float]:
        templates = dict(self.registry.get("facility_templates") or {})
        default = dict(templates.get("default") or {})
        exact = templates.get(facility)
        if isinstance(exact, dict):
            default.update(exact)
        return {
            "main_capacity_kva": _safe_float(default.get("main_capacity_kva"), 250.0),
            "sheddable_capacity_kva": _safe_float(default.get("sheddable_capacity_kva"), 35.0),
            "deferrable_capacity_kva": _safe_float(default.get("deferrable_capacity_kva"), 25.0),
        }

    def _ensure_devices(self) -> None:
        devices = self.state.setdefault("devices", {})
        families = dict(self.registry.get("product_families") or {})
        for facility in list(self.registry.get("facilities") or []):
            template = self._facility_template(str(facility))
            slug = _slug(facility)
            definitions = [
                {
                    "device_id": f"ACB-{slug}",
                    "product_key": "masterpact_mtz",
                    "panel": "Main LV Switchboard",
                    "load_group": "Main facility incomer",
                    "classification": "critical",
                    "capacity_kva": template["main_capacity_kva"],
                    "actuation_allowed": False,
                    "command_capability": "monitor_only",
                },
                {
                    "device_id": f"MCCB-{slug}-01",
                    "product_key": "compact_nsx",
                    "panel": "Controllable Feeder Panel",
                    "load_group": "Sheddable feeder",
                    "classification": "sheddable",
                    "capacity_kva": template["sheddable_capacity_kva"],
                    "actuation_allowed": True,
                    "command_capability": "open_close",
                },
                {
                    "device_id": f"CT-{slug}-01",
                    "product_key": "tesys_island",
                    "panel": "Motor Control Centre",
                    "load_group": "Deferrable motor/HVAC/pump group",
                    "classification": "deferrable",
                    "capacity_kva": template["deferrable_capacity_kva"],
                    "actuation_allowed": True,
                    "command_capability": "run_stop_defer",
                },
            ]
            for definition in definitions:
                device_id = definition["device_id"]
                family = dict(families.get(definition["product_key"]) or {})
                current = dict(devices.get(device_id) or {})
                current.update({
                    **definition,
                    "facility_id": str(facility),
                    "facility_name": str(facility),
                    "manufacturer": family.get("manufacturer", "Schneider Electric"),
                    "product_family": family.get("family", definition["product_key"]),
                    "device_type": family.get("device_type"),
                    "role": family.get("role"),
                    "communication": current.get("communication", "online"),
                    "health": current.get("health", "healthy"),
                    "control_mode": current.get("control_mode", "remote"),
                    "contact_state": current.get("contact_state", "closed"),
                    "ack_state": current.get("ack_state", "idle"),
                    "last_command_id": current.get("last_command_id"),
                    "last_action_utc": current.get("last_action_utc"),
                })
                devices[device_id] = current

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _simulator_state(self) -> dict[str, Any]:
        return self._read_json(self.simulator_state_path)

    def _approval_state(self) -> dict[str, Any]:
        return self._read_json(self.approval_store_path)

    def _system_settings(self) -> dict[str, Any]:
        return self._read_json(self.system_settings_path)

    def _value(self, payload: Mapping[str, object], *keys: str) -> object | None:
        for key in keys:
            if key in payload and payload.get(key) not in (None, ""):
                return payload.get(key)
        return None

    def _text_value(self, payload: Mapping[str, object], *keys: str) -> str:
        value = self._value(payload, *keys)
        if isinstance(value, Mapping):
            nested = self._value(value, "name", "label", "id", "facility_name", "facility_id")
            return str(nested or "").strip()
        return str(value or "").strip()

    def _approval_status(self, payload: Mapping[str, object]) -> str:
        value = self._value(
            payload,
            "decision_status",
            "approval_status",
            "operator_decision",
            "decision",
            "state",
            "status",
        )
        if isinstance(value, Mapping):
            value = self._value(value, "status", "decision", "state", "value")
        text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "approve": "approved",
            "authorise": "approved",
            "authorize": "approved",
            "authorised": "approved",
            "authorized": "approved",
            "accepted": "approved",
        }
        if text in aliases:
            text = aliases[text]
        if text:
            return text
        if payload.get("approved") is True or payload.get("approved_by_operator") is True:
            return "approved"
        return ""

    def _action_collections(self, card: Mapping[str, object]) -> list[Mapping[str, object]]:
        result: list[Mapping[str, object]] = []
        for key in (
            "actions",
            "approved_actions",
            "planned_actions",
            "response_actions",
            "operator_actions",
            "action_items",
        ):
            value = card.get(key)
            if isinstance(value, list):
                result.extend(x for x in value if isinstance(x, Mapping))
            elif isinstance(value, Mapping):
                nested = value.get("items") or value.get("actions")
                if isinstance(nested, list):
                    result.extend(x for x in nested if isinstance(x, Mapping))
                elif any(k in value for k in ("reduction_kva", "requested_reduction_kva", "classification", "load_group")):
                    result.append(value)

        plan = card.get("action_plan")
        if isinstance(plan, list):
            result.extend(x for x in plan if isinstance(x, Mapping))
        elif isinstance(plan, Mapping):
            nested = plan.get("actions") or plan.get("items")
            if isinstance(nested, list):
                result.extend(x for x in nested if isinstance(x, Mapping))
            elif any(k in plan for k in ("reduction_kva", "requested_reduction_kva", "classification", "load_group")):
                result.append(plan)

        if not result and any(
            key in card
            for key in (
                "reduction_kva",
                "requested_reduction_kva",
                "safe_reduction_kva",
                "planned_reduction_kva",
                "target_reduction_kva",
            )
        ):
            result.append(card)
        return result

    def _candidate_approval_cards(self, payload: Mapping[str, object]) -> list[Mapping[str, object]]:
        cards: list[Mapping[str, object]] = []
        seen_ids: set[int] = set()

        def add(value: object) -> None:
            if isinstance(value, Mapping):
                ident = id(value)
                if ident in seen_ids:
                    return
                seen_ids.add(ident)
                cards.append(value)
            elif isinstance(value, list):
                for item in value:
                    add(item)

        for key in (
            "recommendations",
            "items",
            "cards",
            "records",
            "recommendation_records",
            "decisions",
            "approval_records",
        ):
            value = payload.get(key)
            if isinstance(value, Mapping):
                add(list(value.values()))
            else:
                add(value)

        deck = payload.get("approval_deck")
        if isinstance(deck, Mapping):
            for key in ("items", "cards", "records"):
                value = deck.get(key)
                if isinstance(value, Mapping):
                    add(list(value.values()))
                else:
                    add(value)

        def walk(value: object, depth: int = 0) -> None:
            if depth > 5:
                return
            if isinstance(value, Mapping):
                status = self._approval_status(value)
                has_identity = any(k in value for k in ("recommendation_id", "id", "action_id"))
                has_actions = bool(self._action_collections(value))
                if status and has_identity and has_actions:
                    add(value)
                for nested in value.values():
                    if isinstance(nested, (Mapping, list)):
                        walk(nested, depth + 1)
            elif isinstance(value, list):
                for nested in value:
                    if isinstance(nested, (Mapping, list)):
                        walk(nested, depth + 1)

        walk(payload)
        return cards

    def _normalise_classification(self, action: Mapping[str, object], card: Mapping[str, object]) -> str:
        raw = self._value(action, "classification", "load_class", "load_type")
        if raw is None:
            group = action.get("load_group")
            if isinstance(group, Mapping):
                raw = self._value(group, "classification", "load_class", "type")
        if raw is None:
            raw = self._value(card, "classification", "load_class", "load_type")
        text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
        if text in {"defer", "deferred", "shiftable", "scheduled", "deferrable_load"}:
            return "deferrable"
        if text in {"shed", "curtailable", "curtailed", "noncritical", "non_critical", "sheddable_load"}:
            return "sheddable"
        if text in {"protected", "essential"}:
            return "critical"
        return text

    def _normalise_reduction(self, action: Mapping[str, object], card: Mapping[str, object]) -> float:
        keys = (
            "reduction_kva",
            "requested_reduction_kva",
            "safe_reduction_kva",
            "planned_reduction_kva",
            "target_reduction_kva",
            "authorised_reduction_kva",
            "authorized_reduction_kva",
        )
        for source in (action, card):
            value = self._value(source, *keys)
            if value not in (None, ""):
                return max(_safe_float(value, 0.0), 0.0)
        return 0.0

    def _record_is_current(self, card: Mapping[str, object], action: Mapping[str, object]) -> bool:
        for source in (action, card):
            if source.get("current") is False:
                return False
            if source.get("execution_available") is False:
                return False
            if source.get("stale") is True or source.get("expired") is True:
                return False

        sim = self._simulator_state()
        boundary = _parse_time(sim.get("current_data_boundary") or sim.get("latest_released_timestamp"))
        next_target = _parse_time(sim.get("next_forecast_target"))
        target = None
        for source in (action, card):
            target = _parse_time(
                self._value(
                    source,
                    "target_timestamp",
                    "forecast_timestamp",
                    "starts_at",
                    "start_timestamp",
                )
            )
            if target is not None:
                break

        if target is None:
            if card.get("current") is True or card.get("execution_available") is True:
                return True
            return True

        if boundary is not None and target < boundary:
            return False
        if next_target is not None and target > next_target:
            return False
        return True

    def _approved_actions(self) -> list[dict[str, Any]]:
        payload = self._approval_state()
        cards = self._candidate_approval_cards(payload)
        result: list[dict[str, Any]] = []
        seen: set[str] = set()

        for card_index, card in enumerate(cards):
            if self._approval_status(card) != "approved":
                continue
            recommendation_id = self._text_value(card, "recommendation_id", "id", "recommendationId")
            actions = self._action_collections(card)
            for index, raw in enumerate(actions):
                action = dict(raw)
                if not self._record_is_current(card, action):
                    continue

                facility_name = self._text_value(
                    action,
                    "facility_name",
                    "facility",
                    "site_name",
                    "facility_id",
                ) or self._text_value(
                    card,
                    "facility_name",
                    "facility",
                    "site_name",
                    "facility_id",
                )
                facility_id = self._text_value(action, "facility_id") or self._text_value(card, "facility_id") or facility_name
                classification = self._normalise_classification(action, card)
                reduction = self._normalise_reduction(action, card)

                group_value = self._value(action, "load_group_name", "load_group", "group_name", "load_name")
                if isinstance(group_value, Mapping):
                    group_name = self._text_value(group_value, "name", "label", "load_group_name", "id")
                else:
                    group_name = str(group_value or "").strip()

                action["facility_id"] = facility_id
                action["facility_name"] = facility_name
                action["recommendation_id"] = recommendation_id
                action["classification"] = classification
                action["reduction_kva"] = reduction
                action["load_group_name"] = group_name or str(action.get("load_group_name") or action.get("load_group") or "")
                action["approved_by_operator"] = True
                action["simulator_source"] = self._text_value(action, "simulator_source") or self._text_value(card, "simulator_source")
                action.setdefault(
                    "operator",
                    self._text_value(card, "operator", "decision_operator", "approved_by", "operator_name")
                    or "dashboard-operator",
                )

                action_key = str(
                    self._value(action, "action_id", "id", "command_id")
                    or f"{recommendation_id or 'record-'+str(card_index)}:{index}:{action['facility_name']}:{action['load_group_name']}:{classification}:{reduction:.3f}"
                )
                if action_key in seen:
                    continue
                seen.add(action_key)
                action["_action_key"] = action_key
                result.append(action)

        history_sources: list[object] = []
        for key in ("action_history", "approved_actions", "authorised_actions", "authorized_actions"):
            history_sources.append(payload.get(key))

        for collection in history_sources:
            if not isinstance(collection, list):
                continue
            for index, raw in enumerate(collection):
                if not isinstance(raw, Mapping):
                    continue
                status = self._approval_status(raw)
                if status and status not in {"approved", "executed", "recorded", "authorised", "authorized"}:
                    continue
                if raw.get("approved_by_operator") is False:
                    continue
                action = dict(raw)
                if not self._record_is_current(raw, action):
                    continue
                action["classification"] = self._normalise_classification(action, raw)
                action["reduction_kva"] = self._normalise_reduction(action, raw)
                action["facility_name"] = self._text_value(action, "facility_name", "facility", "facility_id")
                action["facility_id"] = self._text_value(action, "facility_id") or action["facility_name"]
                action["recommendation_id"] = self._text_value(action, "recommendation_id")
                action["simulator_source"] = self._text_value(action, "simulator_source") or self._text_value(raw, "simulator_source")
                action["approved_by_operator"] = True
                key = str(
                    self._value(action, "action_id", "id", "command_id")
                    or f"history:{index}:{action.get('recommendation_id')}:{action.get('facility_name')}:{action.get('reduction_kva')}"
                )
                if key in seen:
                    continue
                seen.add(key)
                action["_action_key"] = key
                result.append(action)

        return result

    def _approval_bridge_status(self) -> dict[str, Any]:
        payload = self._approval_state()
        cards = self._candidate_approval_cards(payload)
        approved_cards = [card for card in cards if self._approval_status(card) == "approved"]
        actions = self._approved_actions()
        commands = list(self.state.get("commands", []))
        rejected = [c for c in commands if str(c.get("status")) == "rejected"]
        return {
            "store_path": str(self.approval_store_path),
            "store_exists": self.approval_store_path.exists(),
            "candidate_records": len(cards),
            "approved_records": len(approved_cards),
            "approved_current_actions": len(actions),
            "processed_action_keys": len(self.state.get("processed_action_keys", [])),
            "commands_created": len(commands),
            "commands_rejected": len(rejected),
            "last_rejection": rejected[-1].get("detail") if rejected else None,
        }

    def _facility_device_candidates(self, facility: str, classification: str) -> list[dict[str, Any]]:
        norm = _normalise(facility)
        matches = []
        for device in self.state.get("devices", {}).values():
            device_norm = _normalise(device.get("facility_name")) or _normalise(device.get("facility_id"))
            if not (device_norm == norm or (len(norm) >= 5 and norm in device_norm) or (len(device_norm) >= 5 and device_norm in norm)):
                continue
            if str(device.get("classification")) != classification:
                continue
            matches.append(dict(device))
        return matches

    def _validate_action(self, action: Mapping[str, object]) -> tuple[dict[str, Any], float]:
        classification = str(action.get("classification") or "").lower()
        if classification in BLOCKED_CLASSIFICATIONS or classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError("Critical or unclassified loads cannot reach the actuation gateway.")
        if not bool(action.get("approved_by_operator", True)):
            raise ValueError("Actuation requires an operator-approved action.")
        facility = str(action.get("facility_name") or action.get("facility_id") or "").strip()
        if not facility:
            raise ValueError("Approved action has no facility mapping.")
        candidates = self._facility_device_candidates(facility, classification)
        if not candidates:
            raise ValueError(f"No {classification} device is mapped to {facility}.")
        device = candidates[0]
        if not bool(device.get("actuation_allowed")):
            raise ValueError("Selected device is monitor-only.")
        if str(device.get("communication")) != "online":
            raise ValueError("Selected control device is offline.")
        if str(device.get("control_mode")) != "remote":
            raise ValueError("Selected control device is in local/manual mode.")
        if str(device.get("health")) != "healthy":
            raise ValueError("Selected control device is not healthy.")
        requested = max(_safe_float(action.get("reduction_kva"), 0.0), 0.0)
        if requested <= 0:
            raise ValueError("Approved action has no positive reduction target.")
        capacity = max(_safe_float(device.get("capacity_kva"), 0.0), 0.0)
        safe_reduction = min(requested, capacity)
        if safe_reduction <= 0:
            raise ValueError("Device has no safe controllable capacity.")
        return device, safe_reduction

    def _command_for_action(self, action: Mapping[str, object], device: Mapping[str, object], safe_reduction: float) -> dict[str, Any]:
        sim = self._simulator_state()
        now_sim = _parse_time(sim.get("current_data_boundary") or sim.get("latest_released_timestamp"))
        starts = _parse_time(action.get("starts_at") or action.get("start_timestamp") or action.get("target_timestamp"))
        if starts is None:
            starts = _parse_time(sim.get("next_forecast_target")) or now_sim
        duration = int(_safe_float(action.get("duration_minutes"), 30.0) or 30)
        duration = max(1, min(duration, 720))
        ends = _parse_time(action.get("ends_at")) or (starts + timedelta(minutes=duration) if starts else None)
        classification = str(action.get("classification"))
        action_name = str(action.get("action") or ("defer_load" if classification == "deferrable" else "shed_load"))
        target_state = "off" if classification == "deferrable" else "open"
        return {
            "command_id": "ACT-" + uuid.uuid4().hex[:14].upper(),
            "action_key": str(action.get("_action_key")),
            "recommendation_id": str(action.get("recommendation_id") or ""),
            "facility_id": str(action.get("facility_id") or action.get("facility_name") or ""),
            "facility_name": str(action.get("facility_name") or action.get("facility_id") or ""),
            "load_group": str(action.get("load_group") or action.get("load_group_name") or ""),
            "load_group_name": str(action.get("load_group_name") or action.get("load_group") or ""),
            "classification": classification,
            "action": action_name,
            "requested_reduction_kva": round(_safe_float(action.get("reduction_kva")), 3),
            "commanded_reduction_kva": round(safe_reduction, 3),
            "device_id": str(device.get("device_id")),
            "device_family": str(device.get("product_family")),
            "target_state": target_state,
            "operator": str(action.get("operator") or "dashboard-operator"),
            "simulator_source": str(action.get("simulator_source") or sim.get("source") or ""),
            "issued_utc": _iso(),
            "issued_wall_epoch": _utcnow().timestamp(),
            "starts_at": starts.isoformat() if starts else None,
            "ends_at": ends.isoformat() if ends else None,
            "duration_minutes": duration,
            "status": "queued",
            "transport": SOURCE_MODE,
            "live_switching": False,
            "safety_checks": {
                "operator_approved": True,
                "critical_load_excluded": True,
                "device_online": True,
                "remote_mode": True,
                "device_healthy": True,
                "capacity_clamped": safe_reduction < _safe_float(action.get("reduction_kva")),
            },
        }

    def _advance_commands(self) -> None:
        now_epoch = _utcnow().timestamp()
        sim = self._simulator_state()
        sim_time = _parse_time(sim.get("current_data_boundary") or sim.get("latest_released_timestamp"))
        simulator_source = str(sim.get("source") or "")
        devices = self.state.get("devices", {})
        changed = False
        for command in self.state.get("commands", []):
            status = str(command.get("status"))
            if status in {"rejected", "failed", "completed", "superseded"}:
                continue
            command_source = str(command.get("simulator_source") or "")
            if simulator_source and command_source and command_source != simulator_source:
                command["status"] = "superseded"
                command["superseded_utc"] = _iso()
                device = devices.get(str(command.get("device_id")))
                if device and device.get("last_command_id") == command.get("command_id"):
                    device["contact_state"] = "closed"
                    device["ack_state"] = "superseded"
                    device["last_action_utc"] = command["superseded_utc"]
                self._log("COMMAND_SUPERSEDED", command_id=command.get("command_id"), simulator_source=simulator_source)
                changed = True
                continue
            starts = _parse_time(command.get("starts_at"))
            ends = _parse_time(command.get("ends_at"))
            if sim_time is not None and ends is not None and sim_time >= ends:
                command["status"] = "completed"
                command["completed_utc"] = _iso()
                device = devices.get(str(command.get("device_id")))
                if device:
                    device["contact_state"] = "closed"
                    device["ack_state"] = "completed"
                    device["last_action_utc"] = command["completed_utc"]
                self._log("COMMAND_COMPLETED", command_id=command.get("command_id"), device_id=command.get("device_id"))
                changed = True
                continue
            elapsed = max(now_epoch - _safe_float(command.get("issued_wall_epoch"), now_epoch), 0.0)
            if elapsed < 0.35:
                new_status = "queued"
            elif elapsed < 0.75:
                new_status = "dispatched"
            elif elapsed < 1.15:
                new_status = "acknowledged"
            else:
                new_status = "scheduled" if sim_time is not None and starts is not None and sim_time < starts else "executed"
            if new_status != status:
                command["status"] = new_status
                command[f"{new_status}_utc"] = _iso()
                self._log("COMMAND_STATE", command_id=command.get("command_id"), status=new_status, device_id=command.get("device_id"))
                changed = True
            device = devices.get(str(command.get("device_id")))
            if device:
                device["last_command_id"] = command.get("command_id")
                device["ack_state"] = "acknowledged" if new_status in {"acknowledged", "executed"} else new_status
                if new_status == "executed":
                    device["contact_state"] = command.get("target_state")
                    device["last_action_utc"] = command.get("executed_utc") or _iso()
                elif new_status == "scheduled":
                    device["contact_state"] = "closed"
        if changed:
            self._save()

    def sync_from_approvals(self) -> dict[str, Any]:
        with self._lock:
            self._ensure_devices()
            simulator_source = str(self._simulator_state().get("source") or "")
            if simulator_source:
                if str(self.state.get("last_simulator_source") or "") != simulator_source:
                    self.state["peak_emulated_reduction_kva"] = 0.0
                self.state["last_simulator_source"] = simulator_source
            self._advance_commands()
            processed = set(str(x) for x in self.state.get("processed_action_keys", []))
            for action in self._approved_actions():
                key = str(action.get("_action_key"))
                if not key or key in processed:
                    continue
                try:
                    device, safe = self._validate_action(action)
                    command = self._command_for_action(action, device, safe)
                    self.state.setdefault("commands", []).append(command)
                    self._log(
                        "COMMAND_QUEUED",
                        command_id=command["command_id"],
                        recommendation_id=command["recommendation_id"],
                        facility=command["facility_name"],
                        device_id=command["device_id"],
                        reduction_kva=command["commanded_reduction_kva"],
                        classification=command["classification"],
                    )
                except Exception as exc:
                    self.state.setdefault("commands", []).append({
                        "command_id": "ACT-" + uuid.uuid4().hex[:14].upper(),
                        "action_key": key,
                        "recommendation_id": str(action.get("recommendation_id") or ""),
                        "facility_name": str(action.get("facility_name") or action.get("facility_id") or ""),
                        "status": "rejected",
                        "issued_utc": _iso(),
                        "detail": str(exc),
                        "live_switching": False,
                    })
                    self._log("COMMAND_REJECTED", action_key=key, detail=str(exc))
                processed.add(key)
            self.state["processed_action_keys"] = sorted(processed)
            self.state["last_sync_utc"] = _iso()
            self._advance_commands()
            impact = self._impact_locked()
            self.state["peak_emulated_reduction_kva"] = max(
                _safe_float(self.state.get("peak_emulated_reduction_kva")),
                _safe_float(impact["metrics"].get("current_reduction_kva")),
            )
            self._save()
            return self.status(sync=False)

    def _command_active_at(self, command: Mapping[str, object], sim_time: datetime | None) -> bool:
        if str(command.get("status")) != "executed" or sim_time is None:
            return False
        starts = _parse_time(command.get("starts_at"))
        ends = _parse_time(command.get("ends_at"))
        if starts and sim_time < starts:
            return False
        if ends and sim_time >= ends:
            return False
        return True

    @staticmethod
    def _command_matches_session(command: Mapping[str, object], simulator_source: str, sim_time: datetime | None) -> bool:
        command_source = str(command.get("simulator_source") or "")
        if simulator_source and command_source:
            return simulator_source == command_source
        if command_source and not simulator_source:
            return False
        if simulator_source and not command_source:
            # Compatibility for commands written before session provenance was stored:
            # retain them only while their original time window is currently active.
            starts = _parse_time(command.get("starts_at"))
            ends = _parse_time(command.get("ends_at"))
            return sim_time is not None and (starts is None or sim_time >= starts) and (ends is None or sim_time < ends)
        return True

    def _impact_locked(self) -> dict[str, Any]:
        sim = self._simulator_state()
        sim_time = _parse_time(sim.get("current_data_boundary") or sim.get("latest_released_timestamp"))
        simulator_source = str(sim.get("source") or "")
        relevant = [
            c for c in self.state.get("commands", [])
            if self._command_matches_session(c, simulator_source, sim_time)
        ]
        accepted = [c for c in relevant if str(c.get("status")) not in {"rejected", "failed", "superseded"}]
        active = [c for c in accepted if self._command_active_at(c, sim_time)]
        executed = [c for c in accepted if str(c.get("status")) in {"executed", "completed"}]
        pending = [c for c in accepted if str(c.get("status")) != "completed"]
        current = sum(_safe_float(c.get("commanded_reduction_kva")) for c in active)
        authorised = sum(_safe_float(c.get("commanded_reduction_kva")) for c in pending)
        commanded = sum(
            _safe_float(c.get("commanded_reduction_kva"))
            for c in pending
            if str(c.get("status")) in {"dispatched", "acknowledged", "scheduled", "executed"}
        )
        peak = max(_safe_float(self.state.get("peak_emulated_reduction_kva")), current)

        shifted_kwh = 0.0
        curtailed_kwh = 0.0
        energy_value = 0.0
        settings = self._system_settings()
        op = dict(settings.get("operational") or {})
        peak_rate = _safe_float(op.get("peak_energy_usd_per_kwh"), 0.23)
        standard_rate = _safe_float(op.get("standard_energy_usd_per_kwh"), 0.13)
        offpeak_rate = _safe_float(op.get("offpeak_energy_usd_per_kwh"), 0.06)
        assumed_pf = 0.95
        for command in executed:
            kva = _safe_float(command.get("commanded_reduction_kva"))
            hours = max(_safe_float(command.get("duration_minutes"), 30.0), 0.0) / 60.0
            kwh = kva * assumed_pf * hours
            if str(command.get("classification")) == "deferrable":
                shifted_kwh += kwh
                energy_value += kwh * max(peak_rate - offpeak_rate, 0.0)
            else:
                curtailed_kwh += kwh
                energy_value += kwh * peak_rate
        metrics = {
            "approved_actions": len(accepted),
            "authorised_reduction_kva": round(authorised, 3),
            "approved_peak_reduction_plan_kva": round(authorised, 3),
            "commanded_reduction_kva": round(commanded, 3),
            "device_confirmed_reduction_kva": round(current, 3),
            "current_reduction_kva": round(current, 3),
            "peak_reduction_kva": round(peak, 3),
            "peak_period_energy_shifted_kwh": round(shifted_kwh, 3),
            "peak_period_energy_curtailed_kwh": round(curtailed_kwh, 3),
            "approved_energy_cost_saving_estimate_usd": round(energy_value, 2),
            "approved_demand_charge_saving_estimate_usd": 0.0,
            "approved_reactive_charge_saving_estimate_usd": 0.0,
            "approved_total_cost_saving_estimate_usd": round(energy_value, 2),
            "demand_charge_protection_status": "hardware_emulation_only",
            "approved_saving_estimate_basis": "Hardware-emulated device execution and configured tariff rates; not a realised invoice saving.",
            "critical_load_violations": 0,
            "actuation_mode": SOURCE_MODE,
            "impact_verification_level": "hardware_emulation",
            "active_command_count": len(active),
            "scheduled_command_count": len([c for c in pending if str(c.get("status")) == "scheduled"]),
            "completed_command_count": len([c for c in accepted if str(c.get("status")) == "completed"]),
            "next_restoration_at": min(
                (str(c.get("ends_at")) for c in active if c.get("ends_at")),
                default=None,
            ),
        }
        actions = []
        for command in relevant:
            if str(command.get("status")) in {"rejected", "failed", "superseded"}:
                continue
            command_active = self._command_active_at(command, sim_time)
            starts = _parse_time(command.get("starts_at"))
            status = str(command.get("status"))
            lifecycle_phase = (
                "active" if command_active
                else "restored" if status == "completed"
                else "scheduled" if sim_time is not None and starts is not None and sim_time < starts
                else status
            )
            actions.append({
                "command_id": command.get("command_id"),
                "recommendation_id": command.get("recommendation_id"),
                "facility_id": command.get("facility_id"),
                "facility_name": command.get("facility_name"),
                "load_group_name": command.get("load_group_name"),
                "classification": command.get("classification"),
                "phase": command.get("status"),
                "lifecycle_phase": lifecycle_phase,
                "active": command_active,
                "reduction_kva": command.get("commanded_reduction_kva"),
                "source_tariff_period": "peak",
                "destination_tariff_period": "offpeak" if command.get("classification") == "deferrable" else None,
                "estimated_energy_cost_saving_usd": 0.0,
                "starts_at": command.get("starts_at"),
                "ends_at": command.get("ends_at"),
                "duration_minutes": command.get("duration_minutes"),
                "simulator_source": command.get("simulator_source"),
                "control_command": {
                    "status": command.get("status"),
                    "mode": SOURCE_MODE,
                    "device_id": command.get("device_id"),
                    "acknowledged": str(command.get("status")) in {"acknowledged", "scheduled", "executed", "completed"},
                    "live_switching": False,
                },
            })
        return {
            "active": True,
            "mode": SOURCE_MODE,
            "simulated_timestamp": sim.get("current_data_boundary"),
            "metrics": metrics,
            "actions": actions,
            "control_gateway": {
                "mode": SOURCE_MODE,
                "ready": True,
                "live_enabled": False,
                "device_confirmation": True,
                "gateway_id": (self.registry.get("gateway") or {}).get("gateway_id"),
                "safety_boundary": "Commands are hardware-emulated. Critical loads are excluded. No physical switching occurs until a commissioned live gateway is explicitly enabled in a future release.",
            },
            "claim_boundary": "Actuation response is hardware-emulated. Real verified savings require commissioned electrical hardware plus post-command meter feedback.",
        }

    def impact(self) -> dict[str, Any]:
        with self._lock:
            self.sync_from_approvals()
            return self._impact_locked()

    def devices(self, facility: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            self._advance_commands()
            items = [deepcopy(v) for v in self.state.get("devices", {}).values()]
            if facility:
                norm = _normalise(facility)
                items = [x for x in items if _normalise(x.get("facility_name")) == norm or _normalise(x.get("facility_id")) == norm]
            items.sort(key=lambda x: (str(x.get("facility_name")), str(x.get("classification")), str(x.get("device_id"))))
            return items

    def facilities(self) -> list[str]:
        return sorted({str(x.get("facility_name")) for x in self.devices() if x.get("facility_name")})

    def commands(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            self._advance_commands()
            return deepcopy(list(self.state.get("commands", []))[-max(1, min(limit, 500)):][::-1])

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.event_log_path.exists():
            return []
        rows = []
        for line in self.event_log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, min(limit, 500)):]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows[::-1]

    def status(self, *, sync: bool = True) -> dict[str, Any]:
        with self._lock:
            if sync:
                # sync_from_approvals() re-enters through an RLock.
                self.sync_from_approvals()
            devices = self.devices()
            commands = self.commands(50)
            return {
                "status": "ready",
                "mode": SOURCE_MODE,
                "gateway": {
                    **dict(self.registry.get("gateway") or {}),
                    "status": "connected",
                    "last_sync_utc": self.state.get("last_sync_utc"),
                    "live_control_enabled": False,
                },
                "facilities": self.facilities(),
                "device_count": len(devices),
                "online_devices": len([d for d in devices if d.get("communication") == "online"]),
                "remote_ready_devices": len([d for d in devices if d.get("communication") == "online" and d.get("control_mode") == "remote" and d.get("health") == "healthy"]),
                "commands": commands,
                "latest_command": commands[0] if commands else None,
                "approval_bridge": self._approval_bridge_status(),
                "impact": self._impact_locked(),
                "claim_boundary": "This release emulates connected control hardware. It never sends a live breaker/contactor command.",
            }

    def set_emulated_device_state(self, device_id: str, *, communication: str | None = None, control_mode: str | None = None, health: str | None = None) -> dict[str, Any]:
        with self._lock:
            device = self.state.get("devices", {}).get(device_id)
            if not device:
                raise KeyError(device_id)
            if communication is not None:
                if communication not in {"online", "offline"}:
                    raise ValueError("communication must be online or offline")
                device["communication"] = communication
            if control_mode is not None:
                if control_mode not in {"remote", "local"}:
                    raise ValueError("control_mode must be remote or local")
                device["control_mode"] = control_mode
            if health is not None:
                if health not in {"healthy", "fault", "tripped"}:
                    raise ValueError("health must be healthy, fault or tripped")
                device["health"] = health
            self._log("DEVICE_EMULATION_STATE", device_id=device_id, communication=device.get("communication"), control_mode=device.get("control_mode"), health=device.get("health"))
            self._save()
            return deepcopy(device)
