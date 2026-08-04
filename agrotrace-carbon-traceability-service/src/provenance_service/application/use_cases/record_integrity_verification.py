from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordIntegrityVerificationCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.audit.entities import AuditEvent


class RecordIntegrityVerification:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordIntegrityVerificationCommand) -> AuditEvent:
        with self._uow_factory() as uow:
            event = self._recorder.record_integrity_verification(uow, cmd)
            uow.commit()
            return event
