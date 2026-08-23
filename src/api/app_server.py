from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.agent.service import AgentService
from src.api.agent_api import build_agent_router
from src.control.actuation_service import ActuationService
from src.control.gateway import ControlGateway


ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_INTERFACE_LANGUAGES = ["en", "sn", "nd", "sw", "zu"]


def create_app(
    project_root: Path | None = None,
    runtime_dir: Path | None = None,
) -> FastAPI:
    """Create the low-memory, software-in-the-loop SIMBA demonstration app."""

    root = Path(project_root or ROOT).resolve()
    agent_runtime = Path(runtime_dir or root / "runtime" / "agent").resolve()

    # This public entry point is deliberately software-only. Environment
    # variables cannot enable live electrical switching.
    os.environ["SIMBA_CONTROL_MODE"] = "simulation"
    os.environ["SIMBA_CONTROL_ALLOW_LIVE"] = "0"
    os.environ.setdefault("SIMBA_AGENT_PROVIDER", "mock")

    actuation = ActuationService(
        root,
        state_path=agent_runtime / "actuation_state.json",
        event_log_path=agent_runtime / "actuation_events.jsonl",
        approval_store_path=agent_runtime / "approval_state.json",
        simulator_state_path=agent_runtime / "simulator_state.json",
        system_settings_path=agent_runtime / "system_settings.json",
    )
    gateway = ControlGateway(mode="simulation", allow_live=False)
    agent = AgentService(
        root,
        runtime_dir=agent_runtime,
        actuation_service=actuation,
        control_gateway=gateway,
    )

    app = FastAPI(
        title="SIMBA Autonomous Energy Operations Agent",
        version="1.1.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.agent_service = agent
    app.include_router(build_agent_router(agent, api_key=None))

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "online",
            "mode": "software_in_the_loop",
            "live_electrical_control": False,
            "interface_languages": SUPPORTED_INTERFACE_LANGUAGES,
            "provider": agent.provider.status(),
        }

    dashboard_dir = root / "dashboard"
    static_dir = dashboard_dir / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    return app
