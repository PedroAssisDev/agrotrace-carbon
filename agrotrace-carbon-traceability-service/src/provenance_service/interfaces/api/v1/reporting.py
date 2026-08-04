"""Reporting-context HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from provenance_service.application.services.provenance_recorder import (
    RecordReportingPeriodCommand,
)
from provenance_service.application.use_cases import RegisterReportingPeriod
from provenance_service.domain.shared.errors import NotFoundError
from provenance_service.interfaces.api.deps import (
    SessionFactoryDep,
    provide_register_reporting_period,
)
from provenance_service.interfaces.api.schemas.reporting import (
    RegisterReportingPeriodRequest,
    ReportingPeriodResponse,
)
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(tags=["reporting"])


@router.post(
    "/reporting-periods",
    response_model=ReportingPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_reporting_period(
    payload: RegisterReportingPeriodRequest,
    use_case: Annotated[
        RegisterReportingPeriod, Depends(provide_register_reporting_period)
    ],
) -> ReportingPeriodResponse:
    cmd = RecordReportingPeriodCommand(**payload.model_dump())
    period = use_case.execute(cmd)
    return ReportingPeriodResponse.model_validate(period)


@router.get(
    "/reporting-periods/{reporting_period_id}",
    response_model=ReportingPeriodResponse,
)
def get_reporting_period(
    reporting_period_id: UUID,
    session_factory: SessionFactoryDep,
) -> ReportingPeriodResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        period = uow.reporting_periods.get(reporting_period_id)
        if period is None:
            raise NotFoundError(f"ReportingPeriod {reporting_period_id} not found")
        return ReportingPeriodResponse.model_validate(period)
