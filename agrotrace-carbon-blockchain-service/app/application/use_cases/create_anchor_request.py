from __future__ import annotations

from app.application.dto.commands import CreateAnchorRequestCommand
from app.domain.entities import AnchorRequest
from app.domain.ports.provenance_ports import ProvenanceEventReaderPort
from app.domain.value_objects.statuses import AnchorRequestStatus
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.clock import utcnow
from app.domain.services.final_publication_gate import require_final_publication_event
from app.shared.constants import EVENT_TO_REQUEST_SCOPE
from app.shared.exceptions import NotFoundError
from app.shared.ids import new_id


class CreateAnchorRequestUseCase:
    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        event_reader: ProvenanceEventReaderPort,
    ) -> None:
        self._uow = uow
        self._event_reader = event_reader
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: CreateAnchorRequestCommand):
        if self._uow.anchor_requests.get_by_source_event_id(command.source_event_id):
            existing = self._uow.anchor_requests.get_by_source_event_id(command.source_event_id)
            return existing.anchor_request_id

        event = self._event_reader.get_event_by_id(command.source_event_id)
        if event is None:
            raise NotFoundError(f"Event not found: {command.source_event_id}")
        require_final_publication_event(event.event_type, context="create_anchor_request")

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
            message="Anchor request created manually",
            correlation_id=event.outbox_event_id,
        )
        return request.anchor_request_id
