from __future__ import annotations

import json

from app.application.dto.commands import ObserveEventsCommand
from app.application.dto.results import ObserveEventsResult
from app.domain.entities import AnchorRequest
from app.domain.ports.provenance_ports import ProvenanceEventReaderPort
from app.domain.value_objects.statuses import AnchorRequestStatus
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.clock import utcnow
from app.shared.constants import ELIGIBLE_ANCHOR_EVENT_TYPES, EVENT_TO_REQUEST_SCOPE
from app.shared.ids import new_id


class ObserveProvenanceEventsUseCase:
    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        event_reader: ProvenanceEventReaderPort,
    ) -> None:
        self._uow = uow
        self._event_reader = event_reader
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: ObserveEventsCommand) -> ObserveEventsResult:
        watermark = self._uow.observer_state.get_watermark()
        events = self._event_reader.fetch_pending_events(
            event_types=set(ELIGIBLE_ANCHOR_EVENT_TYPES),
            after_created_at=watermark,
            limit=command.limit,
        )
        created: list = []
        skipped: list[str] = []
        latest_created_at = watermark

        for event in events:
            if self._uow.anchor_requests.get_by_source_event_id(event.outbox_event_id):
                skipped.append(event.outbox_event_id)
                latest_created_at = max(latest_created_at or event.created_at, event.created_at)
                continue

            now = utcnow()
            request = AnchorRequest(
                anchor_request_id=new_id(),
                source_event_id=event.outbox_event_id,
                source_event_type=event.event_type,
                pipeline_run_id=event.pipeline_run_id,
                calculation_result_set_id=event.calculation_result_set_id,
                reporting_period_id=event.reporting_period_id,
                request_scope=EVENT_TO_REQUEST_SCOPE.get(event.event_type, "manual"),
                status=AnchorRequestStatus.PENDING.value,
                created_at=now,
                updated_at=now,
            )
            self._uow.anchor_requests.add(request)
            self._audit.info(
                event_name="ANCHOR_REQUEST_CREATED",
                entity_type="anchor_request",
                entity_id=str(request.anchor_request_id),
                message=f"Created anchor request from event {event.event_type}",
                correlation_id=event.outbox_event_id,
                context={"event_type": event.event_type},
            )
            created.append(request.anchor_request_id)
            latest_created_at = max(latest_created_at or event.created_at, event.created_at)

        if latest_created_at is not None:
            self._uow.observer_state.set_watermark(latest_created_at)

        return ObserveEventsResult(created_request_ids=created, skipped_event_ids=skipped)
