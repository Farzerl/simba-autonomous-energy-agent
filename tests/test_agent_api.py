from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app_server import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_agent_api_exposes_tools_approval_and_end_to_end_demo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SIMBA_AGENT_PROVIDER", "mock")
    app = create_app(ROOT, tmp_path / "agent")
    with TestClient(app) as client:
        status = client.get("/api/agent/status")
        assert status.status_code == 200
        assert status.json()["live_control_enabled"] is False
        tools = client.get("/api/agent/tools").json()
        assert tools["count"] >= 10
        assert tools["authoritative_safety"] == "deterministic"

        prepared = client.post("/api/agent/demo/start", json={})
        assert prepared.status_code == 200
        mission = prepared.json()
        assert mission["state"] == "AWAITING_APPROVAL"
        completed = client.post(
            f"/api/agent/missions/{mission['mission_id']}/decision",
            json={
                "decision": "approve_with_limits",
                "operator": "api-test-operator",
                "limits": {
                    "max_total_reduction_kva": 250,
                    "max_actions": 20,
                    "allow_dynamic_replanning": True,
                },
            },
        )
        assert completed.status_code == 200
        result = completed.json()
        assert result["state"] == "TARGET_MET"
        assert result["verification"]["target_met"] is True
        assert result["metrics"]["replan_count"] >= 1
        assert result["control_boundary"]["live_control_enabled"] is False


def test_operator_can_modify_or_reject_without_any_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SIMBA_AGENT_PROVIDER", "mock")
    app = create_app(ROOT, tmp_path / "agent-decisions")
    with TestClient(app) as client:
        prepared = client.post(
            "/api/agent/demo/start",
            json={"demo_mode": True, "complication": "underperforming_action"},
        ).json()
        modified = client.post(
            f"/api/agent/missions/{prepared['mission_id']}/decision",
            json={
                "decision": "modify",
                "operator": "operations-lead",
                "modifications": {"reserve_margin_kva": 12},
            },
        )
        assert modified.status_code == 200
        revised = modified.json()
        assert revised["state"] == "AWAITING_APPROVAL"
        assert revised["goal"]["reserve_margin_kva"] == 12
        assert revised["executions"] == []

        rejected = client.post(
            f"/api/agent/missions/{prepared['mission_id']}/decision",
            json={"decision": "reject", "operator": "operations-lead", "note": "Keep observing."},
        )
        assert rejected.status_code == 200
        declined = rejected.json()
        assert declined["state"] == "REJECTED"
        assert declined["executions"] == []
        sequences = [event["sequence"] for event in declined["events"]]
        assert sequences == list(range(1, len(sequences) + 1))


def test_invalid_resilience_mode_and_overly_tight_limits_fail_closed(tmp_path: Path) -> None:
    app = create_app(ROOT, tmp_path / "agent-fail-closed")
    with TestClient(app) as client:
        invalid = client.post(
            "/api/agent/demo/run",
            json={"operator": "operations-lead", "complication": "unknown"},
        )
        assert invalid.status_code == 422

        prepared = client.post("/api/agent/demo/start", json={}).json()
        too_tight = client.post(
            f"/api/agent/missions/{prepared['mission_id']}/decision",
            json={
                "decision": "approve_with_limits",
                "operator": "operations-lead",
                "limits": {"max_total_reduction_kva": 1, "max_actions": 1},
            },
        )
        assert too_tight.status_code == 422
        unchanged = client.get(f"/api/agent/missions/{prepared['mission_id']}").json()
        assert unchanged["state"] == "AWAITING_APPROVAL"
        assert unchanged["executions"] == []
