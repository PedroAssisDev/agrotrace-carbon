from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCalculationParameterSetCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationParameterSet


class RegisterCalculationParameterSet:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCalculationParameterSetCommand) -> CalculationParameterSet:
        with self._uow_factory() as uow:
            param_set = self._recorder.record_calculation_parameter_set(uow, cmd)
            uow.commit()
            return param_set
