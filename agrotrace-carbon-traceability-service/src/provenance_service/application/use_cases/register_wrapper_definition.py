from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordWrapperDefinitionCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import WrapperDefinition


class RegisterWrapperDefinition:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordWrapperDefinitionCommand) -> WrapperDefinition:
        with self._uow_factory() as uow:
            definition = self._recorder.record_wrapper_definition(uow, cmd)
            uow.commit()
            return definition
