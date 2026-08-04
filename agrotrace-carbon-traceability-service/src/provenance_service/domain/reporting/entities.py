"""Reporting-context aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import PeriodGranularity, ReportingPeriodStatus


@dataclass(slots=True)
class ReportingPeriod:
    reporting_period_id: UUID
    period_start: datetime
    period_end: datetime
    period_granularity: PeriodGranularity
    year: int
    period_label: str
    status: ReportingPeriodStatus
    created_at: datetime
    updated_at: datetime
    month: int | None = None
    day: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
