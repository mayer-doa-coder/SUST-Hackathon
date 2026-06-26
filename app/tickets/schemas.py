from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.api.schemas import AnalyzeTicketResponse


class TicketRecord(BaseModel):
    case_id: str
    ticket_id: str
    status: str
    idempotency_key: str
    correlation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response: AnalyzeTicketResponse | None = None
    error_code: str | None = None


class TicketDetailResponse(BaseModel):
    case_id: str
    ticket_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    response: AnalyzeTicketResponse | None = None
    error_code: str | None = None


class TicketStatusResponse(BaseModel):
    case_id: str
    status: str
    message: str


class OutboxEvent(BaseModel):
    event_id: str
    event_type: str
    aggregate_id: str
    correlation_id: str
    payload: dict[str, Any]
    published: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
