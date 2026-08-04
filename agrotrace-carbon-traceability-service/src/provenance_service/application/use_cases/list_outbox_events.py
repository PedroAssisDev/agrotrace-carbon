"""List outbox events with filters and pagination."""

from __future__ import annotations

from dataclasses import dataclass

from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.audit.entities import OutboxEvent


@dataclass(slots=True)
class ListOutboxEventsQuery:
    limit: int = 50
    offset: int = 0
    status: str | None = None
    aggregate_kind: str | None = None
    event_type: str | None = None


@dataclass(slots=True)
class ListOutboxEventsResult:
    items: list[OutboxEvent]
    total: int
    limit: int
    offset: int


class ListOutboxEvents:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, query: ListOutboxEventsQuery) -> ListOutboxEventsResult:
        with self._uow_factory() as uow:
            items, total = uow.outbox.list_filtered(
                limit=query.limit,
                offset=query.offset,
                status=query.status,
                aggregate_kind=query.aggregate_kind,
                event_type=query.event_type,
            )
            return ListOutboxEventsResult(
                items=items,
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
