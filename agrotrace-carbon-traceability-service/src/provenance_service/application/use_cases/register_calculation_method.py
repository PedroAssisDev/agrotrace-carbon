from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCalculationMethodCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationMethod


class RegisterCalculationMethod:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCalculationMethodCommand) -> CalculationMethod:
        with self._uow_factory() as uow:
            method = self._recorder.record_calculation_method(uow, cmd)
            uow.commit()
            return method
