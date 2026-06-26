from __future__ import annotations

from app.workflows.repository import WorkflowConflictError, workflow_repository
from app.workflows.schemas import (
    TERMINAL_STATUSES,
    WORKFLOW_STEPS,
    WorkflowCompensateRequest,
    WorkflowRecord,
    WorkflowResponse,
    WorkflowStartRequest,
    WorkflowStepRequest,
    WorkflowStepResponse,
)


NEXT_STEP = {
    "evidence": "investigation",
    "investigation": "nlg",
    "nlg": None,
}


class WorkflowService:
    def start(self, payload: WorkflowStartRequest) -> WorkflowResponse:
        record, _ = workflow_repository.create_or_get(
            payload.case_id,
            payload.ticket_id,
            payload.idempotency_key,
            payload.correlation_id or "",
        )
        return self._to_response(record)

    def complete_step(self, case_id: str, step: str, payload: WorkflowStepRequest) -> WorkflowStepResponse:
        if step not in WORKFLOW_STEPS:
            raise WorkflowConflictError(f"Unknown workflow step: {step}")

        record = workflow_repository.get(case_id)
        if payload.event_id in record.processed_event_ids:
            return WorkflowStepResponse(case_id=case_id, status=record.status, step=step, idempotent_replay=True)
        if record.status in TERMINAL_STATUSES:
            raise WorkflowConflictError("Cannot update a terminal workflow.")

        record.processed_event_ids.append(payload.event_id)
        record.step_payloads[step] = payload.payload

        if payload.status == "failed":
            if step not in record.failed_steps:
                record.failed_steps.append(step)
            record.status = "failed"
            record.current_step = step
            workflow_repository.save(record)
            return WorkflowStepResponse(case_id=case_id, status=record.status, step=step)

        if step not in record.completed_steps:
            record.completed_steps.append(step)

        next_step = NEXT_STEP[step]
        record.current_step = next_step
        record.status = "completed" if next_step is None else "in_progress"
        workflow_repository.save(record)
        return WorkflowStepResponse(case_id=case_id, status=record.status, step=step)

    def compensate(self, case_id: str, payload: WorkflowCompensateRequest) -> WorkflowResponse:
        record = workflow_repository.get(case_id)
        if payload.event_id and payload.event_id in record.processed_event_ids:
            return self._to_response(record)
        if payload.event_id:
            record.processed_event_ids.append(payload.event_id)
        record.status = "compensated"
        record.current_step = None
        record.compensation_reason = payload.reason
        workflow_repository.save(record)
        return self._to_response(record)

    def retry(self, case_id: str) -> WorkflowResponse:
        record = workflow_repository.get(case_id)
        if record.status != "failed":
            raise WorkflowConflictError("Only failed workflows can be retried.")
        record.retry_count += 1
        record.status = "in_progress"
        record.current_step = record.failed_steps[-1] if record.failed_steps else "evidence"
        workflow_repository.save(record)
        return self._to_response(record)

    def get(self, case_id: str) -> WorkflowResponse:
        return self._to_response(workflow_repository.get(case_id))

    def _to_response(self, record: WorkflowRecord) -> WorkflowResponse:
        return WorkflowResponse(
            case_id=record.case_id,
            ticket_id=record.ticket_id,
            status=record.status,
            current_step=record.current_step,
            completed_steps=record.completed_steps,
            failed_steps=record.failed_steps,
            retry_count=record.retry_count,
            compensation_reason=record.compensation_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


workflow_service = WorkflowService()
