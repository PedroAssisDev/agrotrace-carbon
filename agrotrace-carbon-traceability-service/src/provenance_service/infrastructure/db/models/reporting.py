"""Reporting bounded-context tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from provenance_service.infrastructure.db.models.base import (
    PERIOD_GRANULARITY_T,
    REPORTING_PERIOD_STATUS_T,
    Base,
    UUID_T,
)


def _rep(name: str) -> str:
    return f"reporting_{name}"


class ReportingPeriodModel(Base):
    __tablename__ = _rep("period")
    __table_args__ = (
        UniqueConstraint("period_label", name="uq_reporting_period_period_label"),
        Index("ix_reporting_period_year_month", "year", "month"),
        Index("ix_reporting_period_granularity", "period_granularity"),
    )

    reporting_period_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_granularity: Mapped[str] = mapped_column(PERIOD_GRANULARITY_T, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_label: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(REPORTING_PERIOD_STATUS_T, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )
