from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordResultPublicationCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import ResultPublicationExecution


class RegisterResultPublication:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordResultPublicationCommand) -> ResultPublicationExecution:
        with self._uow_factory() as uow:
            publication = self._recorder.record_result_publication(uow, cmd)
            uow.commit()
            return publication
