from __future__ import annotations

from provenance_service.application.services.provenance_recorder import (
    ProvenanceRecorder,
    RecordResultAggregationLinkCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationResultAggregationLink


class RegisterResultAggregationLink:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder
    ) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(
        self, cmd: RecordResultAggregationLinkCommand
    ) -> CalculationResultAggregationLink:
        with self._uow_factory() as uow:
            link = self._recorder.record_result_aggregation_link(uow, cmd)
            uow.commit()
            return link
