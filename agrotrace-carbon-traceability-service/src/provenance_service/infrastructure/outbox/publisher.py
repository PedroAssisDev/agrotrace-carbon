"""Single-pass outbox dispatcher.

Reads pending events under one UoW, calls the EventPublisher port, and
marks them published or failed in the same transaction. The dispatcher is
intentionally small and synchronous so that it can be invoked from a CLI or
from an APScheduler-driven worker.
"""

from __future__ import annotations

from dataclasses import dataclass

from provenance_service.application.ports import EventPublisher
from provenance_service.application.unit_of_work import UnitOfWork
from provenance_service.infrastructure.observability import get_logger
from provenance_service.infrastructure.outbox._uow_factory import UnitOfWorkFactory


@dataclass(slots=True)
class DispatchSummary:
    fetched: int
    published: int
    failed: int


class OutboxDispatcher:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        publisher: EventPublisher,
        *,
        batch_size: int = 100,
    ) -> None:
        self._uow_factory = uow_factory
        self._publisher = publisher
        self._batch_size = batch_size
        self._log = get_logger("outbox")

    def dispatch_once(self) -> DispatchSummary:
        published = 0
        failed = 0
        with self._uow_factory() as uow:
            uow_typed: UnitOfWork = uow
            pending = uow_typed.outbox.list_pending(self._batch_size)
            for event in pending:
                try:
                    self._publisher.publish(event)
                    uow_typed.outbox.mark_published(event.outbox_event_id)
                    published += 1
                except Exception as exc:  # noqa: BLE001
                    self._log.exception(
                        "outbox.publish_failed",
                        outbox_event_id=str(event.outbox_event_id),
                        event_type=event.event_type,
                        error=str(exc),
                    )
                    uow_typed.outbox.mark_failed(
                        event.outbox_event_id, reason=str(exc) or exc.__class__.__name__
                    )
                    failed += 1
            uow_typed.commit()
            return DispatchSummary(fetched=len(pending), published=published, failed=failed)
