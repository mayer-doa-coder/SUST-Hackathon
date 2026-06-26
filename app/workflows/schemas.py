from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


WORKFLOW_STEPS = ("evidence", "investigation", "nlg")
TERMINAL_STATUSES = {"completed", "failed", "compensated", "manual_review"}


class WorkflowStartRequest(BaseModel):
    case_id: str
    ticket_id: str
    idempotency_key: str
    correlation_id: str | None = None

    model_config = ConfigDict(extra="ignore")


class WorkflowStepRequest(BaseModel):
    event_id: str
    status: str = "completed"
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class WorkflowCompensateRequest(BaseModel):
    reason: str
    event_id: str | None = None

    model_config = ConfigDict(extra="ignore")


class WorkflowRecord(BaseModel):
    case_id: str
    ticket_id: str
    status: str
    idempotency_key: str
    correlation_id: str
    current_step: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    processed_event_ids: list[str] = Field(default_factory=list)
    retry_count: int = 0
    compensation_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    step_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    case_id: str
    ticket_id: str
    status: str
    current_step: str | None
    completed_steps: list[str]
    failed_steps: list[str]
    retry_count: int
    compensation_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowStepResponse(BaseModel):
    case_id: str
    status: str
    step: str
    idempotent_replay: bool = False
