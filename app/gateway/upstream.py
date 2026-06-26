from __future__ import annotations

import httpx
from pydantic import BaseModel, Field

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.config import Settings, get_settings
from app.gateway.middleware import CORRELATION_ID_HEADER
from app.tickets.service import ticket_intake_service


class GatewayUpstreamError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AnalysisStatusResponse(BaseModel):
    case_id: str
    status: str = Field(description="Current gateway-visible analysis state.")
    message: str


class TicketIntakeGatewayClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def analyze(
        self,
        payload: AnalyzeTicketRequest,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> AnalyzeTicketResponse:
        if not self.settings.gateway_upstream_url:
            return await ticket_intake_service.analyze(payload, correlation_id, idempotency_key)

        target = f"{self.settings.gateway_upstream_url.rstrip('/')}/tickets/analyze"
        try:
            async with httpx.AsyncClient(timeout=self.settings.gateway_upstream_timeout_seconds) as client:
                response = await client.post(
                    target,
                    json=payload.model_dump(mode="json"),
                    headers={
                        CORRELATION_ID_HEADER: correlation_id,
                        **({"Idempotency-Key": idempotency_key} if idempotency_key else {}),
                    },
                )
        except httpx.TimeoutException as exc:
            raise GatewayUpstreamError(
                "UPSTREAM_TIMEOUT",
                "Ticket intake service did not respond within the gateway deadline.",
                504,
            ) from exc
        except httpx.HTTPError as exc:
            raise GatewayUpstreamError(
                "UPSTREAM_UNAVAILABLE",
                "Ticket intake service is unavailable.",
                502,
            ) from exc

        if response.status_code >= 500:
            raise GatewayUpstreamError(
                "UPSTREAM_ERROR",
                "Ticket intake service could not complete the request.",
                502,
            )

        if response.status_code >= 400:
            raise GatewayUpstreamError(
                "UPSTREAM_REJECTED_REQUEST",
                "Ticket intake service rejected the request.",
                response.status_code,
            )

        return AnalyzeTicketResponse.model_validate(response.json())

    async def get_analysis(self, case_id: str, correlation_id: str) -> AnalysisStatusResponse:
        if not self.settings.gateway_upstream_url:
            return AnalysisStatusResponse.model_validate(ticket_intake_service.get_status(case_id).model_dump())

        target = f"{self.settings.gateway_upstream_url.rstrip('/')}/tickets/{case_id}/status"
        try:
            async with httpx.AsyncClient(timeout=self.settings.gateway_upstream_timeout_seconds) as client:
                response = await client.get(target, headers={CORRELATION_ID_HEADER: correlation_id})
        except httpx.TimeoutException as exc:
            raise GatewayUpstreamError(
                "UPSTREAM_TIMEOUT",
                "Ticket intake service did not respond within the gateway deadline.",
                504,
            ) from exc
        except httpx.HTTPError as exc:
            raise GatewayUpstreamError(
                "UPSTREAM_UNAVAILABLE",
                "Ticket intake service is unavailable.",
                502,
            ) from exc

        if response.status_code == 404:
            return AnalysisStatusResponse(
                case_id=case_id,
                status="not_found",
                message="Analysis case was not found by ticket intake.",
            )
        if response.status_code >= 400:
            raise GatewayUpstreamError(
                "UPSTREAM_ERROR",
                "Ticket intake service could not return the analysis status.",
                502,
            )

        return AnalysisStatusResponse.model_validate(response.json())
