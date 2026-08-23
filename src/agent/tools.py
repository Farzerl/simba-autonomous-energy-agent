from __future__ import annotations

from typing import Any


TOOL_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "name": "inspect_energy_state",
        "owner": "SIMBA state adapter",
        "deterministic": True,
        "description": "Read compact campus/facility demand, limits, active actions and data freshness.",
    },
    {
        "name": "forecast_demand",
        "owner": "existing Chronos-2 validated router",
        "deterministic": True,
        "description": "Read the existing 30-minute, 2-hour, 6-hour and 24-hour forecast routes without changing weights.",
    },
    {
        "name": "inspect_power_quality",
        "owner": "existing power-quality forecaster",
        "deterministic": True,
        "description": "Read power-factor/reactive-power forecast status and constraints.",
    },
    {
        "name": "classify_tariff_period",
        "owner": "existing ZETDC tariff engine",
        "deterministic": True,
        "description": "Calculate the tariff period and rate used by plan scoring.",
    },
    {
        "name": "detect_anomalies",
        "owner": "existing anomaly logic",
        "deterministic": True,
        "description": "Read anomaly findings; protected loads are escalated rather than controlled.",
    },
    {
        "name": "list_flexible_loads",
        "owner": "scenario load map and hardware emulator",
        "deterministic": True,
        "description": "Return only configured deferrable or sheddable groups and their current emulated device readiness.",
    },
    {
        "name": "estimate_response_effect",
        "owner": "emulator/history response estimator",
        "deterministic": True,
        "description": "Estimate conservative kVA response and confidence from configured emulator/history factors.",
    },
    {
        "name": "rank_candidate_plans",
        "owner": "multi-objective optimizer",
        "deterministic": True,
        "description": "Rank safe plans by target coverage, disruption, confidence, cost and action count.",
    },
    {
        "name": "energy_safety_firewall",
        "owner": "deterministic safety firewall",
        "deterministic": True,
        "description": "Block critical, stale, unavailable, over-capacity, live-control or unapproved actions.",
    },
    {
        "name": "request_mission_approval",
        "owner": "Approval Deck",
        "deterministic": True,
        "description": "Record approve, modify, reject or approve-with-limits before execution.",
    },
    {
        "name": "execute_emulated_action",
        "owner": "existing software-in-the-loop control gateway",
        "deterministic": True,
        "description": "Dispatch only to the simulation transport; live electrical control stays disabled.",
    },
    {
        "name": "verify_and_replan",
        "owner": "mission controller",
        "deterministic": True,
        "description": "Compare realised response with the goal, replan inside approval limits, and close with an audit trail.",
    },
)


def registry_snapshot() -> list[dict[str, Any]]:
    return [dict(item) for item in TOOL_REGISTRY]
