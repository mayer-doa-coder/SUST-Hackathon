from __future__ import annotations

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    name: str
    status: str
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    components: list[ComponentHealth]


class TraceResponse(BaseModel):
    correlation_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: float


class RecentTracesResponse(BaseModel):
    traces: list[TraceResponse]
