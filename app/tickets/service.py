from __future__ import annotations

import hashlib

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.messaging.schemas import PublishEventRequest
from app.messaging.service import pubsub_service
from app.services.analysis import analyze_ticket
from app.tickets.repository import TicketNotFoundError, ticket_repository
from app.tickets.schemas import TicketDetailResponse, TicketStatusResponse
from app.workflows.schemas import WorkflowCompensateRequest, WorkflowStartRequest, WorkflowStepRequest
from app.workflows.service import workflow_service


def _default_idempotency_key(payload: AnalyzeTicketRequest) -> str:
    raw = f"{payload.ticket_id}:{payload.complaint}:{len(payload.transaction_history)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class TicketIntakeService:
    def _emit(self, event_type: str, case_id: str, correlation_id: str, payload: dict) -> None:
        event = ticket_repository.add_outbox_event(event_type, case_id, correlation_id, payload)
        pubsub_service.publish(
            PublishEventRequest(
                event_id=event.event_id,
                event_type=event.event_type,
                case_id=event.aggregate_id,
                correlation_id=event.correlation_id,
                payload=event.payload,
            )
        )

    async def analyze(
        self,
        payload: AnalyzeTicketRequest,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> AnalyzeTicketResponse:
        key = idempotency_key or _default_idempotency_key(payload)
        record, created = ticket_repository.create_or_get(payload.ticket_id, key, correlation_id)

        if not created and record.response is not None:
            return record.response

        if not created and record.status in {"processing", "accepted"}:
            self._emit(
                "TicketAnalysisDuplicateReceived",
                record.case_id,
                correlation_id,
                {"ticket_id": payload.ticket_id, "idempotency_key": key},
            )

        ticket_repository.mark_processing(record.case_id)
        workflow_service.start(
            WorkflowStartRequest(
                case_id=record.case_id,
                ticket_id=payload.ticket_id,
                idempotency_key=key,
                correlation_id=correlation_id,
            )
        )
        self._emit(
            "TicketAnalysisRequested",
            record.case_id,
            correlation_id,
            {
                "ticket_id": payload.ticket_id,
                "idempotency_key": key,
                "transaction_count": len(payload.transaction_history),
            },
        )

        try:
            response = await analyze_ticket(payload)
        except Exception:
            ticket_repository.mark_failed(record.case_id, "ANALYSIS_FAILED")
            workflow_service.compensate(
                record.case_id,
                WorkflowCompensateRequest(reason="ANALYSIS_FAILED", event_id=f"{record.case_id}:compensate:analysis_failed"),
            )
            self._emit(
                "TicketAnalysisFailed",
                record.case_id,
                correlation_id,
                {"ticket_id": payload.ticket_id, "error_code": "ANALYSIS_FAILED"},
            )
            raise

        workflow_service.complete_step(
            record.case_id,
            "evidence",
            WorkflowStepRequest(event_id=f"{record.case_id}:evidence-complete", payload={"transaction_count": len(payload.transaction_history)}),
        )
        workflow_service.complete_step(
            record.case_id,
            "investigation",
            WorkflowStepRequest(
                event_id=f"{record.case_id}:investigation-complete",
                payload={"evidence_verdict": response.evidence_verdict.value, "case_type": response.case_type.value},
            ),
        )
        workflow_service.complete_step(
            record.case_id,
            "nlg",
            WorkflowStepRequest(event_id=f"{record.case_id}:nlg-complete", payload={"safety_checked": True}),
        )
        ticket_repository.mark_completed(record.case_id, response)
        self._emit(
            "TicketAnalysisCompleted",
            record.case_id,
            correlation_id,
            {
                "ticket_id": payload.ticket_id,
                "evidence_verdict": response.evidence_verdict.value,
                "case_type": response.case_type.value,
                "severity": response.severity.value,
                "department": response.department.value,
                "human_review_required": response.human_review_required,
            },
        )
        return response

    def get_ticket(self, case_id: str) -> TicketDetailResponse:
        record = ticket_repository.get(case_id)
        return TicketDetailResponse(
            case_id=record.case_id,
            ticket_id=record.ticket_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            response=record.response,
            error_code=record.error_code,
        )

    def get_status(self, case_id: str) -> TicketStatusResponse:
        try:
            record = ticket_repository.get(case_id)
        except TicketNotFoundError:
            return TicketStatusResponse(
                case_id=case_id,
                status="not_found",
                message="Analysis case was not found by ticket intake.",
            )

        messages = {
            "accepted": "Ticket analysis has been accepted.",
            "processing": "Ticket analysis is in progress.",
            "completed": "Ticket analysis completed successfully.",
            "failed": "Ticket analysis failed and requires review.",
        }
        return TicketStatusResponse(
            case_id=record.case_id,
            status=record.status,
            message=messages.get(record.status, "Ticket analysis status is available."),
        )


ticket_intake_service = TicketIntakeService()
