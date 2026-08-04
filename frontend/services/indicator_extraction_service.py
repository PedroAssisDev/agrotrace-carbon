"""Extração e agregação de variáveis canônicas a partir de ciclos."""

from __future__ import annotations

import calendar
import re
from typing import Any

from utils.formatting import NA as _NA

SUM_ACROSS_CYCLES = frozenset({
    "milk_sales", "organic_fertilizer", "non_organic_fertilizer",
    "electricity_grid", "photovoltaic_energy", "total_feed_input",
    "diesel", "gasoline", "other_fuel",
})

_YEAR_RE = re.compile(r"^\d{4}$")
_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")


def num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_payload_records(cycle: dict) -> list[dict]:
    wrapper = cycle.get("wrapper") or {}
    payload = wrapper.get("normalized_payload") or []
    return [r for r in payload if isinstance(r, dict)]


def record_matches_period(record: dict, reporting_period: str | None) -> bool:
    if not reporting_period:
        return True
    for key in ("period_start", "period_end"):
        val = str(record.get(key) or "")
        if reporting_period in val[:7]:
            return True
    return False


def cycle_records(cycle: dict) -> list[dict]:
    records = extract_payload_records(cycle)
    if records:
        return records
    normalized = cycle.get("normalized_data") or []
    return [r for r in normalized if isinstance(r, dict)]


def extract_variable_from_cycle(
    cycle: dict,
    var_name: str,
    *,
    sum_records: bool = False,
) -> float | None:
    records = cycle_records(cycle)
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if record_matches_period(r, rp)]
    pool = matched or records
    values: list[float] = []
    for r in pool:
        v = num(r.get(var_name))
        if v is None and str(r.get("variable", "")).lower() == var_name.lower():
            v = num(r.get("value"))
        if v is not None:
            values.append(v)
    if not values:
        return None
    if sum_records and matched:
        return sum(values)
    return sum(values) if sum_records else values[-1]


def extract_text_from_cycle(cycle: dict, var_name: str) -> str | None:
    records = cycle_records(cycle)
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if record_matches_period(r, rp)] or records
    for r in reversed(matched):
        raw = r.get(var_name)
        if raw is None and str(r.get("variable", "")).lower() == var_name.lower():
            raw = r.get("value")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def extract_milk_from_cycle(cycle: dict) -> float | None:
    records = cycle_records(cycle)
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if record_matches_period(r, rp)]
    pool = matched or records
    values = []
    for r in pool:
        v = num(r.get("milk_production"))
        if v is None and str(r.get("variable", "")).lower() in ("milk_production", "leite"):
            v = num(r.get("value"))
        if v is not None:
            values.append(v)
    if not values:
        return None
    return sum(values) if matched else values[-1]


def extract_animals_from_cycle(cycle: dict) -> float | None:
    for key in ("lactating_cows", "number_of_lactating_cows"):
        val = extract_variable_from_cycle(cycle, key)
        if val is not None:
            return val
    return None


def aggregate_variable(
    cycles: list[dict],
    var_name: str,
    *,
    mode: str = "latest",
) -> float | None:
    if mode == "sum" or var_name in SUM_ACROSS_CYCLES:
        total = 0.0
        found = False
        for c in cycles:
            v = extract_variable_from_cycle(c, var_name, sum_records=True)
            if v is not None:
                total += v
                found = True
        return total if found else None

    values: list[float] = []
    for c in sorted(cycles, key=lambda x: x.get("reporting_period") or ""):
        v = extract_variable_from_cycle(c, var_name)
        if v is not None:
            values.append(v)

    if not values:
        return None
    if mode == "avg":
        return sum(values) / len(values)
    return values[-1]


def aggregate_animals_representative(cycles: list[dict]) -> tuple[float | None, str]:
    """Agrega rebanho sem supercontagem mensal — média ou último valor."""
    values: list[float] = []
    for c in sorted(cycles, key=lambda x: x.get("reporting_period") or ""):
        v = extract_animals_from_cycle(c)
        if v is not None:
            values.append(v)
    if not values:
        return None, "none"
    if len(values) == 1:
        return values[0], "single"
    return round(sum(values) / len(values), 1), "avg_period"


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _days_for_reporting_period(period: str | None) -> int | None:
    if not period:
        return None
    period = period.strip()
    if _YEAR_RE.match(period):
        return 365
    m = _PERIOD_RE.match(period)
    if m:
        return _days_in_month(int(m.group(1)), int(m.group(2)))
    return None


def estimate_days_in_period(cycles: list[dict], series: list[dict]) -> tuple[int, str]:
    """Estima dias do período analítico para média diária."""
    total_days = 0
    counted = 0
    for c in cycles:
        d = _days_for_reporting_period(c.get("reporting_period"))
        if d:
            total_days += d
            counted += 1
    if total_days > 0:
        return total_days, "real"
    if series:
        return 30 * len(series), "estimated_monthly"
    return 30, "estimated_monthly"


def round_or_na(val: float | None, digits: int = 1) -> Any:
    if val is None:
        return _NA
    return round(val, digits)


def pct_or_na(numerator: float | None, denominator: float | None) -> Any:
    if numerator is None or denominator is None or denominator == 0:
        return _NA
    return round(100.0 * numerator / denominator, 1)


def ratio_or_na(numerator: float | None, denominator: float | None, digits: int = 1) -> Any:
    if numerator is None or denominator is None or denominator == 0:
        return _NA
    return round(numerator / denominator, digits)
