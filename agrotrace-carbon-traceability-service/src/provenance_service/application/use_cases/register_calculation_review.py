from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCalculationReviewCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.calculation.entities import CalculationReview


class RegisterCalculationReview:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCalculationReviewCommand) -> CalculationReview:
        with self._uow_factory() as uow:
            review = self._recorder.record_calculation_review(uow, cmd)
            uow.commit()
            return review
