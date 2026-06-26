from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.observability.registry import observability_registry
from app.observability.schemas import ReadinessResponse, RecentTracesResponse
from app.observability.service import observability_service


router = APIRouter(tags=["observability"])


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    return observability_service.readiness()


@router.get("/observability/health", response_model=ReadinessResponse)
async def observability_health() -> ReadinessResponse:
    return observability_service.readiness()


@router.get("/observability/traces", response_model=RecentTracesResponse)
async def recent_traces() -> RecentTracesResponse:
    return observability_service.recent_traces()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    return observability_registry.metrics_text()
