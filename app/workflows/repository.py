from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock

from app.workflows.schemas import WorkflowRecord


class WorkflowNotFoundError(Exception):
    pass


class WorkflowConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InMemoryWorkflowRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._workflows: dict[str, WorkflowRecord] = {}
        self._idempotency_index: dict[str, str] = {}

    def create_or_get(
        self,
        case_id: str,
        ticket_id: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[WorkflowRecord, bool]:
        with self._lock:
            existing_case_id = self._idempotency_index.get(idempotency_key)
            if existing_case_id:
                return deepcopy(self._require(existing_case_id)), False

            record = WorkflowRecord(
                case_id=case_id,
                ticket_id=ticket_id,
                status="started",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                current_step="evidence",
            )
            self._workflows[case_id] = record
            self._idempotency_index[idempotency_key] = case_id
            return deepcopy(record), True

    def get(self, case_id: str) -> WorkflowRecord:
        with self._lock:
            return deepcopy(self._require(case_id))

    def save(self, record: WorkflowRecord) -> WorkflowRecord:
        with self._lock:
            record.updated_at = datetime.now(UTC)
            self._workflows[record.case_id] = record
            return deepcopy(record)

    def reset(self) -> None:
        with self._lock:
            self._workflows.clear()
            self._idempotency_index.clear()

    def _require(self, case_id: str) -> WorkflowRecord:
        record = self._workflows.get(case_id)
        if record is None:
            raise WorkflowNotFoundError(case_id)
        return record


workflow_repository = InMemoryWorkflowRepository()
