from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCalculationExecutionCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationExecution


class RegisterCalculationExecution:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCalculationExecutionCommand) -> CalculationExecution:
        with self._uow_factory() as uow:
            execution = self._recorder.record_calculation_execution(uow, cmd)
            uow.commit()
            return execution
