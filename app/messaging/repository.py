from __future__ import annotations

from copy import deepcopy
from threading import RLock

from app.domain.enums import Department
from app.messaging.schemas import EventEnvelope, RoutedCase


class InMemoryMessagingRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._events_by_id: dict[str, EventEnvelope] = {}
        self._audit_events: list[EventEnvelope] = []
        self._dead_letters: list[EventEnvelope] = []
        self._routes: dict[Department, list[RoutedCase]] = {department: [] for department in Department}

    def has_event(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._events_by_id

    def record_event(self, event: EventEnvelope) -> None:
        with self._lock:
            self._events_by_id[event.event_id] = event
            self._audit_events.append(event)

    def record_dead_letter(self, event: EventEnvelope) -> None:
        with self._lock:
            self._events_by_id[event.event_id] = event
            self._dead_letters.append(event)
            self._audit_events.append(event)

    def add_route(self, routed_case: RoutedCase) -> None:
        with self._lock:
            routes = self._routes.setdefault(routed_case.department, [])
            if any(item.event_id == routed_case.event_id for item in routes):
                return
            routes.append(routed_case)

    def audit_events(self, case_id: str | None = None) -> list[EventEnvelope]:
        with self._lock:
            events = self._audit_events
            if case_id is not None:
                events = [event for event in events if event.case_id == case_id]
            return deepcopy(events)

    def dead_letters(self) -> list[EventEnvelope]:
        with self._lock:
            return deepcopy(self._dead_letters)

    def routed_cases(self, department: Department) -> list[RoutedCase]:
        with self._lock:
            return deepcopy(self._routes.get(department, []))

    def reset(self) -> None:
        with self._lock:
            self._events_by_id.clear()
            self._audit_events.clear()
            self._dead_letters.clear()
            self._routes = {department: [] for department in Department}


messaging_repository = InMemoryMessagingRepository()
