"""HTTP DTOs for the ``reporting`` bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from provenance_service.domain.shared.enums import PeriodGranularity, ReportingPeriodStatus
from provenance_service.interfaces.api.schemas.common import ReadApiBaseModel, WriteApiBaseModel


class RegisterReportingPeriodRequest(WriteApiBaseModel):
    period_start: datetime
    period_end: datetime
    period_granularity: PeriodGranularity
    year: int = Field(ge=1)
    period_label: str = Field(min_length=1, max_length=64)
    status: ReportingPeriodStatus = ReportingPeriodStatus.OPEN
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)
    reporting_period_id: UUID | None = None


class ReportingPeriodResponse(ReadApiBaseModel):
    reporting_period_id: UUID
    period_start: datetime
    period_end: datetime
    period_granularity: PeriodGranularity
    year: int
    month: int | None
    day: int | None
    period_label: str
    status: ReportingPeriodStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
