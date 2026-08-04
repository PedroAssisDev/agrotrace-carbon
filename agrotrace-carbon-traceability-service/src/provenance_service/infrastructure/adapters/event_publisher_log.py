"""Default :class:`EventPublisher` implementation that just logs."""

from __future__ import annotations

from provenance_service.application.ports import EventPublisher
from provenance_service.domain.audit.entities import OutboxEvent
from provenance_service.infrastructure.observability import get_logger


class LoggingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._log = get_logger("event_publisher")

    def publish(self, event: OutboxEvent) -> None:
        self._log.info(
            "outbox.event",
            outbox_event_id=str(event.outbox_event_id),
            aggregate_kind=event.aggregate_kind,
            aggregate_id=str(event.aggregate_id),
            event_type=event.event_type,
            payload=event.payload,
        )
