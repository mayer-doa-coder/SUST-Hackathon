from __future__ import annotations

from uuid import uuid4

from app.domain.enums import Department, Severity
from app.messaging.repository import messaging_repository
from app.messaging.schemas import EventEnvelope, PublishEventRequest, PublishEventResponse, RoutedCase


class PubSubAuditRoutingService:
    def publish(self, payload: PublishEventRequest) -> PublishEventResponse:
        event_id = payload.event_id or str(uuid4())
        if messaging_repository.has_event(event_id):
            return PublishEventResponse(
                event_id=event_id,
                event_type=payload.event_type,
                case_id=payload.case_id,
                published=False,
                idempotent_replay=True,
            )

        event = EventEnvelope(
            event_id=event_id,
            event_type=payload.event_type,
            case_id=payload.case_id,
            correlation_id=payload.correlation_id,
            schema_version=payload.schema_version,
            payload=payload.payload,
        )

        if payload.payload.get("force_dead_letter"):
            messaging_repository.record_dead_letter(event)
            return PublishEventResponse(
                event_id=event_id,
                event_type=payload.event_type,
                case_id=payload.case_id,
                published=False,
                dead_lettered=True,
            )

        messaging_repository.record_event(event)
        self._dispatch(event)
        return PublishEventResponse(
            event_id=event_id,
            event_type=payload.event_type,
            case_id=payload.case_id,
            published=True,
        )

    def _dispatch(self, event: EventEnvelope) -> None:
        if event.event_type != "TicketAnalysisCompleted":
            return
        department_value = event.payload.get("department")
        if not department_value:
            return
        try:
            department = Department(department_value)
        except ValueError:
            dead_letter = event.model_copy(update={"payload": {**event.payload, "dead_letter_reason": "invalid_department"}})
            messaging_repository.record_dead_letter(dead_letter)
            return

        severity = str(event.payload.get("severity", Severity.LOW.value))
        priority = "high" if severity in {Severity.HIGH.value, Severity.CRITICAL.value} else "normal"
        messaging_repository.add_route(
            RoutedCase(
                case_id=event.case_id,
                department=department,
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                priority=priority,
                payload=event.payload,
            )
        )


pubsub_service = PubSubAuditRoutingService()
