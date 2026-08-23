from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import time
import tracemalloc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.service import AgentService
from src.control.actuation_service import ActuationService
from src.control.gateway import ControlGateway


def _rss_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 3)
    except Exception:
        return None


def _process_peak_rss_mb() -> float | None:
    try:
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return round(value / divisor, 3)
    except Exception:
        return _rss_mb()


def run_once(folder: Path, complication: str) -> dict[str, float | int | bool | str]:
    actuation = ActuationService(
        ROOT,
        state_path=folder / "actuation-state.json",
        event_log_path=folder / "actuation-events.jsonl",
        approval_store_path=folder / "approval.json",
        simulator_state_path=folder / "simulator.json",
        system_settings_path=folder / "settings.json",
    )
    service = AgentService(
        ROOT,
        runtime_dir=folder / "agent",
        actuation_service=actuation,
        control_gateway=ControlGateway(mode="simulation", allow_live=False),
    )
    started = time.perf_counter()
    mission = service.run_demo(complication=complication)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    verification = mission.get("verification") or {}
    return {
        "elapsed_ms": round(elapsed_ms, 3),
        "complication": complication,
        "target_met": bool(verification.get("target_met")),
        "replan_count": int((mission.get("metrics") or {}).get("replan_count", 0)),
        "event_count": len(mission.get("events") or []),
        "action_count": len(mission.get("executions") or []),
        "headroom_kva": float(verification.get("headroom_kva", 0.0)),
        "live_control_enabled": bool((mission.get("control_boundary") or {}).get("live_control_enabled")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "agent_gate1_benchmark.json")
    args = parser.parse_args()
    args.runs = max(1, min(args.runs, 30))
    timings: list[float] = []
    results: list[dict[str, float | int | bool | str]] = []
    tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix="simba-agent-benchmark-") as temporary:
        base = Path(temporary)
        for index in range(args.runs):
            complication = "device_unavailable" if index % 2 == 0 else "underperforming_action"
            result = run_once(base / f"run-{index + 1}", complication)
            results.append(result)
            timings.append(float(result["elapsed_ms"]))
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    report = {
        "benchmark": "SIMBA deterministic software-in-the-loop resilience mission",
        "scope_note": "This is a deterministic synthetic-fixture application benchmark, not the official ADTC llama.cpp/GGUF profiler result.",
        "runs": args.runs,
        "latency_ms": {
            "mean": round(statistics.mean(timings), 3),
            "median": round(statistics.median(timings), 3),
            "minimum": round(min(timings), 3),
            "maximum": round(max(timings), 3),
        },
        "python_tracemalloc_peak_mb": round(peak_bytes / (1024 * 1024), 3),
        "process_peak_rss_mb": _process_peak_rss_mb(),
        "resource_note": "process_peak_rss_mb uses the operating-system high-water mark on Linux/macOS and a process RSS sample on Windows; Python tracemalloc is reported separately.",
        "all_targets_met": all(bool(item["target_met"]) for item in results),
        "all_live_control_disabled": not any(bool(item["live_control_enabled"]) for item in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
