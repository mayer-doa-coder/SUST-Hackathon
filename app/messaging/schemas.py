from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Department


class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    case_id: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "event.v1"
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PublishEventRequest(BaseModel):
    event_type: str
    case_id: str
    correlation_id: str = ""
    event_id: str | None = None
    schema_version: str = "event.v1"
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PublishEventResponse(BaseModel):
    event_id: str
    event_type: str
    case_id: str
    published: bool
    idempotent_replay: bool = False
    dead_lettered: bool = False


class AuditEventResponse(BaseModel):
    events: list[EventEnvelope]


class RoutedCase(BaseModel):
    case_id: str
    department: Department
    event_id: str
    correlation_id: str
    priority: str
    payload: dict[str, Any]
    routed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RoutedCasesResponse(BaseModel):
    department: Department
    cases: list[RoutedCase]


class DeadLetterResponse(BaseModel):
    events: list[EventEnvelope]
