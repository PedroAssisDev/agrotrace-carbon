"""Expansão de séries temporais a partir de normalized_data (eixo X vs badge)."""

from __future__ import annotations

import re
from typing import Any

from utils.global_filter import MONTH_LABELS, cycle_granularity, cycle_period, format_cycle_period_label
from utils.property_filter import normalize_property_id

_YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cycle_records(cycle: dict) -> list[dict]:
    wrapper = cycle.get("wrapper") or {}
    payload = [r for r in (wrapper.get("normalized_payload") or []) if isinstance(r, dict)]
    normalized = [r for r in (cycle.get("normalized_data") or []) if isinstance(r, dict)]
    if len(normalized) > len(payload):
        return normalized
    if payload:
        return payload
    return normalized


def resolve_series_granularity(cycle: dict) -> str:
    """Granularidade para eixo X (annual | monthly | daily)."""
    coverage = cycle.get("temporal_coverage") or {}
    kind = coverage.get("kind")
    source = coverage.get("source_granularity") or coverage.get("granularity")
    if kind == "annual_multiyear":
        return "annual"
    if kind == "monthly_to_year":
        return "monthly"
    if kind == "daily_range":
        return "daily"
    if source == "monthly":
        return "monthly"
    g = cycle_granularity(cycle)
    if g == "daily":
        return "daily"
    if g == "annual":
        return "annual"
    return "monthly"


def extract_record_period_key(record: dict, granularity: str) -> str | None:
    """Chave sortável por registro normalizado."""
    if granularity == "annual":
        year = record.get("year")
        if year is not None:
            return str(int(year))
        ctx = record.get("_temporal_context") or {}
        start = ctx.get("start") or ctx.get("value")
        if start and len(str(start)) >= 4:
            return str(start)[:4]
        return None

    if granularity == "monthly":
        for key in ("period_start", "period_end"):
            val = record.get(key)
            if isinstance(val, str) and len(val) >= 7:
                return val[:7]
        ctx = record.get("_temporal_context") or {}
        start = ctx.get("start")
        if isinstance(start, str) and len(start) >= 7:
            return start[:7]
        return None

    if granularity == "daily":
        date = record.get("date")
        if isinstance(date, str) and date.strip():
            return date.strip()[:10]
        ctx = record.get("_temporal_context") or {}
        val = ctx.get("value") or ctx.get("start")
        if val:
            return str(val)[:10]
        return None

    return None


def period_chart_label(key: str, granularity: str) -> str:
    """Label para eixo X — nunca usa intervalo agregado (ex.: 2021 a 2025)."""
    if not key:
        return "—"
    if granularity == "annual":
        return key[:4] if len(key) >= 4 else key
    if granularity == "monthly" and len(key) >= 7 and key[4] == "-":
        year, month = key[:4], key[5:7]
        return f"{MONTH_LABELS.get(month, month)}/{year}"
    if granularity == "daily" and len(key) >= 10 and key[4] == "-":
        year, month, day = key[:4], key[5:7], key[8:10]
        return f"{day}/{month}"
    return key


def _chart_label_for_cycle_period(period: str | None, granularity: str) -> str:
    """Label de eixo X para um ciclo único (evita format_period_label em ranges)."""
    if not period:
        return "—"
    p = period.strip()
    if _YEAR_RANGE.match(p):
        return p.split("-")[1]
    if granularity == "annual" and len(p) == 4 and p.isdigit():
        return p
    if granularity == "monthly" and len(p) >= 7:
        return period_chart_label(p[:7], "monthly")
    if granularity == "daily" and "/" in p:
        start = p.split("/")[0]
        if len(start) >= 10:
            return period_chart_label(start[:10], "daily")
    return period_chart_label(p, granularity)


def _extract_milk_from_record(record: dict) -> float | None:
    for key in ("total_milk_production", "milk_production", "milk"):
        v = _num(record.get(key))
        if v is not None:
            return v
    var = str(record.get("variable") or "").lower()
    if var in ("milk_production", "milk", "leite", "total_milk_production"):
        return _num(record.get("value"))
    return None


def _extract_co2e_from_record(record: dict) -> float | None:
    total = 0.0
    found = False
    for key in ("co2e_total_kg", "enteric_tco2e", "total_co2e", "co2e_kg"):
        v = _num(record.get(key))
        if v is not None:
            total += v
            found = True
    return total if found else None


def expand_cycle_temporal_rows(cycle: dict) -> list[dict]:
    """Expande normalized_data em pontos temporais para gráficos."""
    if not cycle or not cycle.get("cycle_id"):
        return []

    granularity = resolve_series_granularity(cycle)
    records = _cycle_records(cycle)
    if not records:
        return _single_cycle_row(cycle, granularity)

    buckets: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = extract_record_period_key(rec, granularity)
        if not key:
            continue
        bucket = buckets.setdefault(key, {
            "period_key": key,
            "milk_liters": 0.0,
            "milk_count": 0,
            "co2e_kg": 0.0,
            "co2e_count": 0,
            "record_count": 0,
        })
        bucket["record_count"] += 1
        milk = _extract_milk_from_record(rec)
        if milk is not None:
            bucket["milk_liters"] += milk
            bucket["milk_count"] += 1
        co2e = _extract_co2e_from_record(rec)
        if co2e is not None:
            bucket["co2e_kg"] += co2e
            bucket["co2e_count"] += 1

    if not buckets:
        return _single_cycle_row(cycle, granularity)

    rows: list[dict] = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        milk = b["milk_liters"] if b["milk_count"] else None
        co2e = b["co2e_kg"] if b["co2e_count"] else None
        intensity = (co2e / milk) if co2e is not None and milk and milk > 0 else None
        rows.append(_make_row(
            cycle,
            period=key,
            period_key=key,
            period_label=period_chart_label(key, granularity),
            milk_liters=milk,
            co2e_kg=co2e,
            intensity=intensity,
        ))

    if len(rows) == 1 and len(records) == 1:
        return _single_cycle_row(cycle, granularity)
    return rows


def _single_cycle_row(cycle: dict, granularity: str) -> list[dict]:
    period = cycle_period(cycle)
    if not period:
        return []
    key = period
    if _YEAR_RANGE.match(period or ""):
        key = period.split("-")[1]
    label = _chart_label_for_cycle_period(period, granularity)
    calc = cycle.get("calculation") or {}
    milk = _extract_milk_from_cycle_simple(cycle)
    co2e = _num(calc.get("co2e_total_kg"))
    intensity = _num(calc.get("co2e_intensity_per_milk_liter"))
    return [_make_row(
        cycle,
        period=period,
        period_key=key,
        period_label=label,
        milk_liters=milk,
        co2e_kg=co2e,
        intensity=intensity,
    )]


def _make_row(
    cycle: dict,
    *,
    period: str,
    period_key: str,
    period_label: str,
    milk_liters: float | None,
    co2e_kg: float | None,
    intensity: float | None,
) -> dict:
    return {
        "period": period,
        "period_key": period_key,
        "period_label": period_label,
        "cycle_id": cycle.get("cycle_id"),
        "property_id": normalize_property_id(cycle),
        "property_name": cycle.get("property_name"),
        "milk_liters": milk_liters,
        "co2e_kg": co2e_kg,
        "intensity": intensity,
        "status": cycle.get("current_status") or cycle.get("status"),
        "integrity": (cycle.get("integrity") or {}).get("final_status")
        or (cycle.get("integrity") or {}).get("is_valid"),
    }


def cycle_period_display_label(cycle: dict | None) -> str:
    """Label para badge/resumo (pode ser cobertura agregada)."""
    return format_cycle_period_label(cycle)


def expand_cycles_period_series(cycles: list[dict]) -> list[dict]:
    """Série temporal para indicadores: delega ao modelo temporal (base de cálculo)."""
    from utils.temporal_model import (
        build_base_series_from_cycles,
        infer_input_granularity,
        resolve_calculation_base_granularity,
    )

    ref = cycles[0] if cycles else {}
    calc_base = resolve_calculation_base_granularity(infer_input_granularity(ref))
    return [p.to_dict() for p in build_base_series_from_cycles(cycles, calc_base)]


def _extract_milk_from_cycle_simple(cycle: dict) -> float | None:
    records = _cycle_records(cycle)
    if not records:
        return None
    values = [_extract_milk_from_record(r) for r in records]
    values = [v for v in values if v is not None]
    if not values:
        return None
    granularity = resolve_series_granularity(cycle)
    if granularity == "daily" and len(records) > 1:
        return sum(values)
    return sum(values)


_TEMPORAL_MODEL_EXPORTS = frozenset({
    "TemporalModel",
    "TimeSeriesPoint",
    "aggregate_to_view",
    "build_base_series_from_cycles",
    "build_temporal_model",
    "empty_temporal_model",
    "infer_input_granularity",
    "resolve_calculation_base_granularity",
})


def __getattr__(name: str):
    if name in _TEMPORAL_MODEL_EXPORTS:
        import utils.temporal_model as tm
        return getattr(tm, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
