from __future__ import annotations

from provenance_service.application.services.provenance_recorder import (
    ProvenanceRecorder,
    RecordReportingPeriodCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.reporting.entities import ReportingPeriod


class RegisterReportingPeriod:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder
    ) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordReportingPeriodCommand) -> ReportingPeriod:
        with self._uow_factory() as uow:
            period = self._recorder.record_reporting_period(uow, cmd)
            uow.commit()
            return period
