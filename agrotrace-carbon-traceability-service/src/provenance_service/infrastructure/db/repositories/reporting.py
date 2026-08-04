"""SQLAlchemy implementation of the reporting-context repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from provenance_service.domain.reporting.entities import ReportingPeriod
from provenance_service.infrastructure.db.models.reporting import ReportingPeriodModel
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemyReportingPeriodRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, period: ReportingPeriod) -> None:
        self._session.add(M.to_reporting_period_model(period))

    def get(self, reporting_period_id: UUID) -> ReportingPeriod | None:
        m = get_model_or_pending(
            self._session, ReportingPeriodModel, "reporting_period_id", reporting_period_id
        )
        return M.from_reporting_period_model(m) if m else None

    def get_by_label(self, period_label: str) -> ReportingPeriod | None:
        m = self._session.scalar(
            select(ReportingPeriodModel).where(
                ReportingPeriodModel.period_label == period_label
            )
        )
        return M.from_reporting_period_model(m) if m else None

    def list_all(self) -> list[ReportingPeriod]:
        rows = self._session.scalars(select(ReportingPeriodModel)).all()
        return [M.from_reporting_period_model(m) for m in rows]
