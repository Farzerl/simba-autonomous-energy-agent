from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class SafetyFinding:
    rule_id: str
    passed: bool
    message: str
    severity: str = "block"


@dataclass
class SafetyResult:
    allowed: bool
    findings: list[SafetyFinding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "findings": [asdict(item) for item in self.findings]}


class EnergySafetyFirewall:
    """Authoritative deterministic boundary for every proposed/emulated action."""

    ALLOWED_CLASSIFICATIONS = {"deferrable", "sheddable"}
    ALLOWED_ACTIONS = {"defer_load", "shed_load"}
    SAFE_MODES = {"software_in_the_loop", "hardware_emulation", "simulation", "dry_run"}

    @staticmethod
    def _utc(value: object) -> datetime | None:
        if value in (None, ""):
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def check_action(
        self,
        action: Mapping[str, Any],
        *,
        device: Mapping[str, Any] | None,
        approval_status: str,
        limits: Mapping[str, Any] | None = None,
        require_approval: bool = True,
    ) -> SafetyResult:
        findings: list[SafetyFinding] = []

        def add(rule_id: str, passed: bool, message: str) -> None:
            findings.append(SafetyFinding(rule_id, passed, message))

        classification = str(action.get("classification", "critical"))
        add(
            "critical-load-exclusion",
            classification in self.ALLOWED_CLASSIFICATIONS and not bool(action.get("critical_load")),
            "Only configured deferrable or sheddable loads may be controlled.",
        )
        add(
            "supported-action",
            str(action.get("action", "")) in self.ALLOWED_ACTIONS,
            "The action must be a supported defer/shed operation.",
        )
        mode = str(action.get("control_mode", "software_in_the_loop"))
        add("software-only-boundary", mode in self.SAFE_MODES, "Execution must remain software-in-the-loop or hardware emulation.")
        add("live-control-lock", not bool(action.get("live_control_enabled")), "Live electrical control must remain disabled.")
        reduction = float(action.get("reduction_kva", 0.0) or 0.0)
        maximum = float(action.get("maximum_available_kva", 0.0) or 0.0)
        add("positive-bounded-response", 0.0 < reduction <= maximum + 1e-6, "Requested response must be positive and within configured flexibility.")
        projected = float(action.get("projected_facility_kva", 0.0) or 0.0)
        critical_floor = float(action.get("critical_floor_kva", 0.0) or 0.0)
        add("critical-floor", projected + 1e-6 >= critical_floor, "Projected facility demand may not cross the critical-load floor.")

        if device is None:
            add("configured-device", False, "A configured emulated device is required.")
        else:
            add("configured-device", bool(device.get("device_id")), "A configured emulated device is required.")
            add("device-online", str(device.get("communication")) == "online", "The emulated device must be online.")
            add("device-healthy", str(device.get("health")) == "healthy", "The emulated device must be healthy.")
            add("remote-mode", str(device.get("control_mode")) == "remote", "The emulated device must be in remote mode.")
            add("actuation-allowed", bool(device.get("actuation_allowed")), "The configured device must permit emulated actuation.")

        expires_at = self._utc(action.get("expires_at"))
        add("stale-command-protection", expires_at is None or expires_at > datetime.now(timezone.utc), "Expired actions cannot execute.")
        add("operator-approval", (not require_approval) or approval_status == "approved", "An operator approval is required before execution.")

        constraints = dict(limits or {})
        permitted = {str(item) for item in constraints.get("permitted_facilities", [])}
        prohibited = {str(item) for item in constraints.get("prohibited_load_groups", [])}
        add(
            "facility-scope",
            not permitted or str(action.get("facility_id")) in permitted or str(action.get("facility_name")) in permitted,
            "The action must remain inside the operator-approved facility scope.",
        )
        add(
            "load-group-scope",
            str(action.get("load_group")) not in prohibited,
            "The load group must not be prohibited by the operator.",
        )
        return SafetyResult(allowed=all(item.passed for item in findings), findings=findings)

    def check_plan(
        self,
        actions: list[Mapping[str, Any]],
        *,
        device_lookup: Mapping[str, Mapping[str, Any]],
        approval_status: str,
        limits: Mapping[str, Any] | None = None,
        require_approval: bool = True,
    ) -> dict[str, Any]:
        constraints = dict(limits or {})
        checks = [
            self.check_action(
                action,
                device=device_lookup.get(str(action.get("device_id"))),
                approval_status=approval_status,
                limits=constraints,
                require_approval=require_approval,
            )
            for action in actions
        ]
        plan_findings: list[SafetyFinding] = []
        max_actions = constraints.get("max_actions")
        if max_actions is not None:
            plan_findings.append(SafetyFinding("maximum-action-count", len(actions) <= int(max_actions), "Plan action count must remain inside approval limits."))
        max_reduction = constraints.get("max_total_reduction_kva")
        if max_reduction is not None:
            total = sum(float(item.get("reduction_kva", 0.0) or 0.0) for item in actions)
            plan_findings.append(SafetyFinding("maximum-total-reduction", total <= float(max_reduction) + 1e-6, "Plan response must remain inside the approved kVA limit."))
        allowed = all(item.allowed for item in checks) and all(item.passed for item in plan_findings)
        return {
            "allowed": allowed,
            "action_checks": [item.as_dict() for item in checks],
            "plan_findings": [asdict(item) for item in plan_findings],
        }
