from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app_server import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_lightweight_server_runs_both_safe_resilience_scenarios(tmp_path: Path) -> None:
    with TestClient(create_app(ROOT, tmp_path / "agent")) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["live_electrical_control"] is False
        assert set(health.json()["interface_languages"]) == {"en", "sn", "nd", "sw", "zu"}

        for complication in ("device_unavailable", "underperforming_action"):
            response = client.post(
                "/api/agent/demo/run",
                json={
                    "operator": "test-operator",
                    "approval_mode": "approve_with_limits",
                    "complication": complication,
                },
            )
            assert response.status_code == 200
            mission = response.json()
            assert mission["state"] == "TARGET_MET"
            assert mission["complication"] == complication
            assert mission["verification"]["target_met"] is True
            assert mission["metrics"]["replan_count"] >= 1
            assert mission["metrics"]["critical_load_actions"] == 0
            assert mission["control_boundary"]["live_control_enabled"] is False


def test_localised_operator_interface_is_served(tmp_path: Path) -> None:
    with TestClient(create_app(ROOT, tmp_path / "agent")) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert 'id="agent-language"' in page.text
        assert "ChiShona" in page.text
        assert "isiNdebele" in page.text
        language_script = client.get("/static/i18n.js")
        assert language_script.status_code == 200
        assert "simba-agent-language" in language_script.text
        assert "UMGOMO UQINISEKISIWE" in language_script.text
