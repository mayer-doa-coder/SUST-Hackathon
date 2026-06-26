from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from app.api.schemas import AnalyzeTicketResponse
from app.tickets.schemas import OutboxEvent, TicketRecord


class TicketNotFoundError(Exception):
    pass


class InMemoryTicketRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._tickets: dict[str, TicketRecord] = {}
        self._idempotency_index: dict[str, str] = {}
        self._outbox: list[OutboxEvent] = []

    def create_or_get(
        self,
        ticket_id: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> tuple[TicketRecord, bool]:
        with self._lock:
            existing_case_id = self._idempotency_index.get(idempotency_key)
            if existing_case_id:
                return deepcopy(self._tickets[existing_case_id]), False

            case_id = ticket_id
            record = TicketRecord(
                case_id=case_id,
                ticket_id=ticket_id,
                status="accepted",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            self._tickets[case_id] = record
            self._idempotency_index[idempotency_key] = case_id
            return deepcopy(record), True

    def mark_processing(self, case_id: str) -> None:
        self._update_status(case_id, "processing")

    def mark_completed(self, case_id: str, response: AnalyzeTicketResponse) -> None:
        with self._lock:
            record = self._require(case_id)
            record.status = "completed"
            record.response = response
            record.updated_at = datetime.now(UTC)

    def mark_failed(self, case_id: str, error_code: str) -> None:
        with self._lock:
            record = self._require(case_id)
            record.status = "failed"
            record.error_code = error_code
            record.updated_at = datetime.now(UTC)

    def get(self, case_id: str) -> TicketRecord:
        with self._lock:
            return deepcopy(self._require(case_id))

    def add_outbox_event(
        self,
        event_type: str,
        aggregate_id: str,
        correlation_id: str,
        payload: dict,
    ) -> OutboxEvent:
        with self._lock:
            event = OutboxEvent(
                event_id=str(uuid4()),
                event_type=event_type,
                aggregate_id=aggregate_id,
                correlation_id=correlation_id,
                payload=payload,
            )
            self._outbox.append(event)
            return deepcopy(event)

    def list_outbox(self) -> list[OutboxEvent]:
        with self._lock:
            return deepcopy(self._outbox)

    def reset(self) -> None:
        with self._lock:
            self._tickets.clear()
            self._idempotency_index.clear()
            self._outbox.clear()

    def _update_status(self, case_id: str, status: str) -> None:
        with self._lock:
            record = self._require(case_id)
            record.status = status
            record.updated_at = datetime.now(UTC)

    def _require(self, case_id: str) -> TicketRecord:
        record = self._tickets.get(case_id)
        if record is None:
            raise TicketNotFoundError(case_id)
        return record


ticket_repository = InMemoryTicketRepository()
