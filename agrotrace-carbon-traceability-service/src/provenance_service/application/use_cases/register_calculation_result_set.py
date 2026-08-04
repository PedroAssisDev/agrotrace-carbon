from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCalculationResultSetCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationResultSet


class RegisterCalculationResultSet:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCalculationResultSetCommand) -> CalculationResultSet:
        with self._uow_factory() as uow:
            result_set = self._recorder.record_calculation_result_set(uow, cmd)
            uow.commit()
            return result_set
