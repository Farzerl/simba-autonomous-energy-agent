from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from src.agent.models import DemoRunRequest, MissionCreateRequest, MissionDecisionRequest
from src.agent.service import AgentService


def build_agent_router(service: AgentService, api_key: str | None = None) -> APIRouter:
    router = APIRouter(tags=["autonomous-agent"])

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if api_key and x_api_key != api_key:
            raise HTTPException(status_code=401, detail="Valid X-API-Key required.")

    def not_found(exc: KeyError) -> HTTPException:
        return HTTPException(status_code=404, detail="Agent mission was not found.")

    @router.get("/api/agent/status")
    def agent_status() -> dict[str, Any]:
        return service.status()

    @router.get("/api/agent/tools")
    def agent_tools() -> dict[str, Any]:
        items = service.tools()
        return {"items": items, "count": len(items), "authoritative_safety": "deterministic"}

    @router.get("/api/agent/missions")
    def agent_missions(limit: int = Query(default=25, ge=1, le=100)) -> dict[str, Any]:
        items = service.missions(limit)
        return {"items": items, "count": len(items)}

    @router.get("/api/agent/missions/{mission_id}")
    def agent_mission(mission_id: str) -> dict[str, Any]:
        try:
            return service.mission(mission_id)
        except KeyError as exc:
            raise not_found(exc) from exc

    @router.post("/api/agent/missions", dependencies=[Depends(require_api_key)])
    def create_agent_mission(payload: MissionCreateRequest | None = None) -> dict[str, Any]:
        try:
            return service.create_mission(payload)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/api/agent/missions/{mission_id}/decision", dependencies=[Depends(require_api_key)])
    def decide_agent_mission(mission_id: str, payload: MissionDecisionRequest) -> dict[str, Any]:
        try:
            return service.decide_mission(
                mission_id,
                payload.decision,
                operator=payload.operator,
                limits=payload.limits,
                modifications=payload.modifications,
                note=payload.note,
            )
        except KeyError as exc:
            raise not_found(exc) from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/api/agent/demo/start", dependencies=[Depends(require_api_key)])
    def start_agent_demo(payload: MissionCreateRequest | None = None) -> dict[str, Any]:
        request = payload or MissionCreateRequest(demo_mode=True, complication="device_unavailable")
        try:
            return service.create_mission(
                MissionCreateRequest(
                    demo_mode=True,
                    scenario_id=request.scenario_id,
                    complication=request.complication,
                    goal=request.goal,
                )
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/api/agent/demo/run", dependencies=[Depends(require_api_key)])
    def run_agent_demo(payload: DemoRunRequest | None = None) -> dict[str, Any]:
        request = payload or DemoRunRequest()
        try:
            return service.run_demo(
                request.operator,
                approval_mode=request.approval_mode,
                complication=request.complication,
            )
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
