from __future__ import annotations

from provenance_service.application.services import ProvenanceRecorder, RecordHashCommand
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.audit.entities import HashRecord


class ComputeAndRecordHash:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordHashCommand) -> HashRecord:
        with self._uow_factory() as uow:
            record = self._recorder.record_hash(uow, cmd)
            uow.commit()
            return record
