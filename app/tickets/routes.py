from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.gateway.middleware import CORRELATION_ID_HEADER
from app.tickets.schemas import TicketDetailResponse, TicketStatusResponse
from app.tickets.service import ticket_intake_service


router = APIRouter(prefix="/tickets", tags=["ticket-intake"])


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", request.headers.get(CORRELATION_ID_HEADER, "")))


@router.post("/analyze", response_model=AnalyzeTicketResponse)
async def analyze_ticket_for_intake(
    payload: AnalyzeTicketRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AnalyzeTicketResponse:
    return await ticket_intake_service.analyze(payload, _correlation_id(request), idempotency_key)


@router.get("/{case_id}", response_model=TicketDetailResponse)
async def get_ticket(case_id: str) -> TicketDetailResponse:
    return ticket_intake_service.get_ticket(case_id)


@router.get("/{case_id}/status", response_model=TicketStatusResponse)
async def get_ticket_status(case_id: str) -> TicketStatusResponse:
    return ticket_intake_service.get_status(case_id)
