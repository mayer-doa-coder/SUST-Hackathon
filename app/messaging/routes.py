from __future__ import annotations

from fastapi import APIRouter

from app.domain.enums import Department
from app.messaging.repository import messaging_repository
from app.messaging.schemas import AuditEventResponse, DeadLetterResponse, PublishEventRequest, PublishEventResponse, RoutedCasesResponse
from app.messaging.service import pubsub_service


router = APIRouter(tags=["pubsub-audit-routing"])


@router.post("/events/publish", response_model=PublishEventResponse)
async def publish_event(payload: PublishEventRequest) -> PublishEventResponse:
    return pubsub_service.publish(payload)


@router.get("/audit/events", response_model=AuditEventResponse)
async def list_audit_events() -> AuditEventResponse:
    return AuditEventResponse(events=messaging_repository.audit_events())


@router.get("/audit/events/{case_id}", response_model=AuditEventResponse)
async def list_case_audit_events(case_id: str) -> AuditEventResponse:
    return AuditEventResponse(events=messaging_repository.audit_events(case_id))


@router.get("/routing/departments/{department}/cases", response_model=RoutedCasesResponse)
async def list_routed_cases(department: Department) -> RoutedCasesResponse:
    return RoutedCasesResponse(department=department, cases=messaging_repository.routed_cases(department))


@router.get("/events/dead-letter", response_model=DeadLetterResponse)
async def list_dead_letters() -> DeadLetterResponse:
    return DeadLetterResponse(events=messaging_repository.dead_letters())
