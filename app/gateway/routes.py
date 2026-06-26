from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.auth.dependencies import require_roles
from app.config import get_settings
from app.gateway.upstream import AnalysisStatusResponse, TicketIntakeGatewayClient


router = APIRouter()
gateway_client = TicketIntakeGatewayClient(get_settings())


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", ""))


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket_route(
    payload: AnalyzeTicketRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: dict | None = Depends(require_roles("support_agent", "admin")),
) -> AnalyzeTicketResponse:
    return await gateway_client.analyze(payload, _correlation_id(request), idempotency_key)


@router.get("/analysis/{case_id}", response_model=AnalysisStatusResponse)
async def analysis_status_route(
    case_id: str,
    request: Request,
    _: dict | None = Depends(require_roles("support_agent", "admin")),
) -> AnalysisStatusResponse:
    return await gateway_client.get_analysis(case_id, _correlation_id(request))
