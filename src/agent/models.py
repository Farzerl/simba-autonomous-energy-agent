from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class _ValueStrEnum(str, Enum):
    """Python 3.10-compatible equivalent of enum.StrEnum's string behaviour."""

    def __str__(self) -> str:
        return str(self.value)


class MissionState(_ValueStrEnum):
    CREATED = "CREATED"
    OBSERVING = "OBSERVING"
    RISK_DETECTED = "RISK_DETECTED"
    PLANNING = "PLANNING"
    PLAN_READY = "PLAN_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    OBSERVING_RESPONSE = "OBSERVING_RESPONSE"
    REPLANNING = "REPLANNING"
    TARGET_MET = "TARGET_MET"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class ApprovalDecision(_ValueStrEnum):
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    APPROVE_WITH_LIMITS = "approve_with_limits"


class MissionGoal(BaseModel):
    peak_limit_kva: float = Field(gt=0, le=100_000)
    target_window_start: str
    target_window_end: str
    critical_load_policy: Literal["exclude"] = "exclude"
    reserve_margin_kva: float = Field(default=5.0, ge=0, le=1_000)
    facility_scope: list[str] = Field(default_factory=list, max_length=100)
    objective: str = Field(
        default="Keep campus demand below the configured peak limit without touching critical loads.",
        min_length=10,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_window(self) -> "MissionGoal":
        if self.target_window_end <= self.target_window_start:
            raise ValueError("target_window_end must be after target_window_start")
        return self


class ApprovalLimits(BaseModel):
    max_total_reduction_kva: float | None = Field(default=None, gt=0, le=100_000)
    max_actions: int | None = Field(default=None, ge=1, le=100)
    permitted_facilities: list[str] = Field(default_factory=list, max_length=100)
    prohibited_load_groups: list[str] = Field(default_factory=list, max_length=100)
    expires_at: str | None = None
    allow_dynamic_replanning: bool = True
    note: str = Field(default="", max_length=500)


class MissionCreateRequest(BaseModel):
    goal: MissionGoal | None = None
    scenario_id: str = Field(default="campus_peak_replay", min_length=3, max_length=100)
    complication: Literal["device_unavailable", "underperforming_action", "none"] = "device_unavailable"
    demo_mode: bool = False


class MissionDecisionRequest(BaseModel):
    decision: ApprovalDecision
    operator: str = Field(default="simba-operator", min_length=2, max_length=100)
    limits: ApprovalLimits | None = None
    modifications: dict[str, Any] = Field(default_factory=dict)
    note: str = Field(default="", max_length=500)


class DemoRunRequest(BaseModel):
    operator: str = Field(default="simba-operator", min_length=2, max_length=100)
    approval_mode: Literal["approve", "approve_with_limits"] = "approve_with_limits"
    complication: Literal["device_unavailable", "underperforming_action"] = "device_unavailable"
