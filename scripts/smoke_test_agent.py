from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.service import AgentService
from src.control.actuation_service import ActuationService
from src.control.gateway import ControlGateway


def run(complication: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="simba-agent-smoke-") as temporary:
        runtime = Path(temporary)
        actuation = ActuationService(
            ROOT,
            state_path=runtime / "actuation_state.json",
            event_log_path=runtime / "actuation_events.jsonl",
            approval_store_path=runtime / "approval_state.json",
            simulator_state_path=runtime / "simulator_state.json",
            system_settings_path=runtime / "system_settings.json",
        )
        mission = AgentService(
            ROOT,
            runtime_dir=runtime / "agent",
            actuation_service=actuation,
            control_gateway=ControlGateway(mode="simulation", allow_live=False),
        ).run_demo(
            "local-smoke-test",
            approval_mode="approve_with_limits",
            complication=complication,
        )

    verification = dict(mission.get("verification") or {})
    metrics = dict(mission.get("metrics") or {})
    checks = {
        "state_target_met": mission.get("state") == "TARGET_MET",
        "target_met": verification.get("target_met") is True,
        "complication_injected": mission.get("complication_injected") is True,
        "replanned": int(metrics.get("replan_count", 0)) >= 1,
        "critical_load_actions": int(metrics.get("critical_load_actions", -1)) == 0,
        "live_control_disabled": dict(mission.get("control_boundary") or {}).get("live_control_enabled") is False,
    }
    return {"complication": complication, "checks": checks, "verification": verification}


def main() -> None:
    results = [run("device_unavailable"), run("underperforming_action")]
    print(json.dumps({"results": results}, indent=2))
    if not all(all(result["checks"].values()) for result in results):
        raise SystemExit("SIMBA agent smoke test failed")


if __name__ == "__main__":
    main()
