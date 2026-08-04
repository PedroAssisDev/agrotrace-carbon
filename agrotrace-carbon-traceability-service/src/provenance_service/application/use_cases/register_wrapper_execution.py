from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordWrapperExecutionCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import WrapperExecution


class RegisterWrapperExecution:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordWrapperExecutionCommand) -> WrapperExecution:
        with self._uow_factory() as uow:
            execution = self._recorder.record_wrapper_execution(uow, cmd)
            uow.commit()
            return execution
