"""Temporalidade — datas e intervalos ISO."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

from .contracts import TemporalDescriptor


def parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%d/%m/%Y").date()
            except ValueError:
                return None
    return None


def date_to_iso(d: date) -> str:
    return d.isoformat()


def interval_for_month(period_date: date) -> tuple[str, str]:
    _, last_day = calendar.monthrange(period_date.year, period_date.month)
    start = period_date.replace(day=1)
    end = period_date.replace(day=last_day)
    return start.isoformat(), end.isoformat()


def interval_for_year(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"


def temporal_instant(observation_date: date) -> TemporalDescriptor:
    return TemporalDescriptor(
        type="instant",
        value=date_to_iso(observation_date),
        granularity="day",
    )


def temporal_interval_month(period_date: date) -> TemporalDescriptor:
    start, end = interval_for_month(period_date)
    return TemporalDescriptor(type="interval", start=start, end=end, granularity="month")


def temporal_interval_year(year: int) -> TemporalDescriptor:
    start, end = interval_for_year(year)
    return TemporalDescriptor(type="interval", start=start, end=end, granularity="year")
