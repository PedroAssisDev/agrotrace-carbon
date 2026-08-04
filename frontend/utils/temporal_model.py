"""Modelo temporal em três camadas: entrada → base de cálculo → visualização.

Camadas:
- ``input_granularity`` — resolução do dado bruto/normalizado.
- ``calculation_base_granularity`` — resolução oficial do cálculo (monthly | annual).
- ``view_granularity`` — agrupamento para gráficos (não cria novos ciclos aprovados).

Documentação: docs/conceptual_model_mrv.md (seções 4–7, 11–12).
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from typing import Any

from utils.global_filter import cycle_granularity, cycle_period, format_cycle_period_label
from utils.temporal_series import (
    _cycle_records,
    _extract_milk_from_cycle_simple,
    _extract_milk_from_record,
    expand_cycle_temporal_rows,
    extract_record_period_key,
    period_chart_label,
)

_YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")

VIEW_GRANULARITY_LABELS = {
    "monthly": "Mensal",
    "quarterly": "Trimestral",
    "semester": "Semestral",
    "annual": "Anual",
    "consolidated": "Consolidado",
}

CALC_BASE_LABELS = {
    "annual": "Anual",
    "monthly": "Mensal",
}


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class TimeSeriesPoint:
    period: str
    period_key: str
    period_label: str
    period_start: str | None = None
    period_end: str | None = None
    milk_liters: float | None = None
    co2e_kg: float | None = None
    intensity: float | None = None
    cycle_id: str | None = None
    approval_status: str | None = None
    cycle_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "period_key": self.period_key,
            "period_label": self.period_label,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "milk_liters": self.milk_liters,
            "co2e_kg": self.co2e_kg,
            "intensity": self.intensity,
            "cycle_id": self.cycle_id,
            "approval_status": self.approval_status,
            "cycle_ids": self.cycle_ids,
        }


@dataclass
class TemporalModel:
    input_granularity: str
    calculation_base_granularity: str
    view_granularity: str
    view_granularity_user: str
    period_display_label: str
    analysis_period_start: str | None
    analysis_period_end: str | None
    base_series: list[TimeSeriesPoint]
    view_series: list[TimeSeriesPoint]
    aggregated_approval_status: str | None
    calculation_points: list[dict[str, Any]] = field(default_factory=list)
    operational_daily_series: list[TimeSeriesPoint] = field(default_factory=list)
    data_mode: str = "include_preliminary"

    def series_as_dicts(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.view_series]

    def base_series_as_dicts(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.base_series]


def infer_input_granularity(cycle: dict | None) -> str:
    if not cycle:
        return "monthly"
    coverage = cycle.get("temporal_coverage") or {}
    kind = coverage.get("kind")
    if kind == "annual_multiyear":
        return "annual"
    if kind == "monthly_to_year":
        return "monthly"
    if kind == "daily_range":
        return "daily"
    data_g = str(cycle.get("data_granularity") or coverage.get("source_granularity") or "").lower()
    if data_g in ("annual", "monthly", "daily", "intraday"):
        return "intraday" if data_g == "intraday" else data_g
    layout = str((cycle.get("wrapper") or {}).get("layout_id") or "").lower()
    if "annual" in layout:
        return "annual"
    if "intraday" in layout or "daily" in layout:
        return "daily"
    if "monthly" in layout:
        return "monthly"
    g = cycle_granularity(cycle)
    if g == "daily":
        return "daily"
    if g == "annual":
        return "annual"
    return "monthly"


def resolve_calculation_base_granularity(input_granularity: str) -> str:
    if input_granularity in ("daily", "intraday"):
        return "monthly"
    if input_granularity == "annual":
        return "annual"
    return "monthly"


def default_view_granularity(calculation_base_granularity: str) -> str:
    if calculation_base_granularity == "annual":
        return "annual"
    return "monthly"


def _approval_key(cycle: dict) -> str:
    from services.cycle_status_service import resolve_managerial_status

    return resolve_managerial_status(cycle).key


def _period_bounds(period_key: str, calc_base: str) -> tuple[str | None, str | None]:
    if calc_base == "annual" and len(period_key) == 4 and period_key.isdigit():
        return f"{period_key}-01-01", f"{period_key}-12-31"
    if calc_base == "monthly" and len(period_key) >= 7 and period_key[4] == "-":
        year, month = int(period_key[:4]), int(period_key[5:7])
        last_day = calendar.monthrange(year, month)[1]
        return f"{period_key}-01", f"{period_key}-{last_day:02d}"
    if len(period_key) >= 10 and period_key[4] == "-":
        return period_key[:10], period_key[:10]
    return None, None


def _point_from_cycle(cycle: dict, calc_base: str) -> TimeSeriesPoint:
    period = cycle_period(cycle) or ""
    key = period
    if period and _YEAR_RANGE.match(period):
        key = period.split("-")[1]
    elif calc_base == "monthly" and len(period) >= 7:
        key = period[:7]
    calc = cycle.get("calculation") or {}
    milk = _extract_milk_from_cycle_simple(cycle)
    co2e = _num(calc.get("co2e_total_kg"))
    intensity = _num(calc.get("co2e_intensity_per_milk_liter"))
    if intensity is None and co2e and milk and milk > 0:
        intensity = co2e / milk
    start, end = _period_bounds(key, calc_base)
    return TimeSeriesPoint(
        period=period,
        period_key=key,
        period_label=period_chart_label(key, calc_base),
        period_start=start,
        period_end=end,
        milk_liters=milk,
        co2e_kg=co2e,
        intensity=intensity,
        cycle_id=cycle.get("cycle_id"),
        approval_status=_approval_key(cycle),
        cycle_ids=[cycle.get("cycle_id")] if cycle.get("cycle_id") else [],
    )


def _dict_row_to_point(row: dict, calc_base: str) -> TimeSeriesPoint:
    key = row.get("period_key") or row.get("period") or ""
    start, end = _period_bounds(key, calc_base)
    return TimeSeriesPoint(
        period=row.get("period") or key,
        period_key=key,
        period_label=row.get("period_label") or period_chart_label(key, calc_base),
        period_start=start,
        period_end=end,
        milk_liters=row.get("milk_liters"),
        co2e_kg=row.get("co2e_kg"),
        intensity=row.get("intensity"),
        cycle_id=row.get("cycle_id"),
        approval_status=row.get("approval_status"),
        cycle_ids=[row.get("cycle_id")] if row.get("cycle_id") else [],
    )


def build_base_series_from_cycles(cycles: list[dict], calc_base: str) -> list[TimeSeriesPoint]:
    if not cycles:
        return []
    if len(cycles) > 1:
        points = [_point_from_cycle(c, calc_base) for c in sorted(cycles, key=lambda x: x.get("reporting_period") or "")]
        return _dedupe_by_period_key(points)

    expanded = expand_cycle_temporal_rows(cycles[0])
    if len(expanded) > 1:
        return [_dict_row_to_point(r, calc_base) for r in expanded]
    if len(expanded) == 1:
        return [_dict_row_to_point(expanded[0], calc_base)]
    return [_point_from_cycle(cycles[0], calc_base)]


def _dedupe_by_period_key(points: list[TimeSeriesPoint]) -> list[TimeSeriesPoint]:
    by_key: dict[str, TimeSeriesPoint] = {}
    for p in points:
        existing = by_key.get(p.period_key)
        if not existing:
            by_key[p.period_key] = p
            continue
        existing.milk_liters = (existing.milk_liters or 0) + (p.milk_liters or 0) or None
        existing.co2e_kg = (existing.co2e_kg or 0) + (p.co2e_kg or 0) or None
        if existing.milk_liters and existing.co2e_kg:
            existing.intensity = existing.co2e_kg / existing.milk_liters
        existing.cycle_ids = list({*(existing.cycle_ids or []), *(p.cycle_ids or [])})
        existing.approval_status = resolve_aggregated_approval_status([existing, p])
    return [by_key[k] for k in sorted(by_key.keys())]


def resolve_aggregated_approval_status(points: list[TimeSeriesPoint]) -> str | None:
    keys = [p.approval_status for p in points if p.approval_status]
    if not keys:
        return None
    if any(k == "rejected" for k in keys):
        return "rejected"
    if all(k in ("approved", "published", "evidence_generated", "integrity_verified") for k in keys):
        return "approved"
    if all(k == keys[0] for k in keys):
        return keys[0]
    if any(k == "pending_approval" for k in keys):
        return "partial_pending"
    return "partial"


def _aggregate_bucket(points: list[TimeSeriesPoint], key: str, label: str, calc_base: str) -> TimeSeriesPoint:
    milk = sum(p.milk_liters or 0 for p in points) or None
    co2e = sum(p.co2e_kg or 0 for p in points) or None
    if milk == 0:
        milk = None
    if co2e == 0:
        co2e = None
    intensity = (co2e / milk) if co2e is not None and milk and milk > 0 else None
    starts = [p.period_start for p in points if p.period_start]
    ends = [p.period_end for p in points if p.period_end]
    cycle_ids: list[str] = []
    for p in points:
        cycle_ids.extend(p.cycle_ids or ([p.cycle_id] if p.cycle_id else []))
    return TimeSeriesPoint(
        period=key,
        period_key=key,
        period_label=label,
        period_start=min(starts) if starts else None,
        period_end=max(ends) if ends else None,
        milk_liters=milk,
        co2e_kg=co2e,
        intensity=intensity,
        approval_status=resolve_aggregated_approval_status(points),
        cycle_ids=sorted(set(cycle_ids)),
    )


def _view_bucket_key(period_key: str, view_granularity: str, calc_base: str) -> tuple[str, str]:
    if view_granularity == "monthly" or calc_base == "monthly" and view_granularity == "monthly":
        if len(period_key) >= 7 and period_key[4] == "-":
            return period_key[:7], period_chart_label(period_key[:7], "monthly")
        return period_key, period_chart_label(period_key, calc_base)

    if view_granularity == "annual":
        year = period_key[:4] if len(period_key) >= 4 else period_key
        return year, year

    if view_granularity == "quarterly" and len(period_key) >= 7 and period_key[4] == "-":
        year, month = int(period_key[:4]), int(period_key[5:7])
        quarter = (month - 1) // 3 + 1
        key = f"{year}-Q{quarter}"
        return key, f"{quarter}º trim/{year}"

    if view_granularity == "semester" and len(period_key) >= 7 and period_key[4] == "-":
        year, month = int(period_key[:4]), int(period_key[5:7])
        sem = 1 if month <= 6 else 2
        key = f"{year}-H{sem}"
        return key, f"{sem}º sem/{year}"

    return period_key, period_chart_label(period_key, calc_base)


def aggregate_to_view(
    base_series: list[TimeSeriesPoint],
    view_granularity: str,
    calc_base: str,
) -> list[TimeSeriesPoint]:
    if not base_series:
        return []
    if view_granularity == "consolidated":
        return [_aggregate_bucket(base_series, "consolidated", "Período consolidado", calc_base)]
    if view_granularity == calc_base or (
        view_granularity == "monthly" and calc_base == "monthly"
    ) or (view_granularity == "annual" and calc_base == "annual"):
        return list(base_series)

    buckets: dict[str, list[TimeSeriesPoint]] = {}
    labels: dict[str, str] = {}
    for p in base_series:
        key, label = _view_bucket_key(p.period_key, view_granularity, calc_base)
        buckets.setdefault(key, []).append(p)
        labels[key] = label

    return [_aggregate_bucket(buckets[k], k, labels[k], calc_base) for k in sorted(buckets.keys())]


def build_operational_daily_series(cycle: dict | None) -> list[TimeSeriesPoint]:
    """Produção diária operacional (não emissão oficial)."""
    if not cycle or infer_input_granularity(cycle) not in ("daily", "intraday"):
        return []
    records = _cycle_records(cycle)
    buckets: dict[str, float] = {}
    for rec in records:
        key = extract_record_period_key(rec, "daily")
        if not key:
            continue
        milk = _extract_milk_from_record(rec)
        if milk is not None:
            buckets[key] = buckets.get(key, 0.0) + milk
    return [
        TimeSeriesPoint(
            period=k,
            period_key=k,
            period_label=period_chart_label(k, "daily"),
            period_start=k,
            period_end=k,
            milk_liters=v,
            cycle_id=cycle.get("cycle_id"),
            cycle_ids=[cycle.get("cycle_id")] if cycle.get("cycle_id") else [],
        )
        for k, v in sorted(buckets.items())
    ]


def build_analysis_period_display_label(cycles: list[dict], calc_base: str) -> str:
    if not cycles:
        return "—"
    if len(cycles) == 1:
        return format_cycle_period_label(cycles[0])
    keys = sorted({cycle_period(c) or "" for c in cycles if cycle_period(c)})
    if not keys:
        return "—"
    if len(keys) == 1:
        return period_chart_label(keys[0][:7] if calc_base == "monthly" and len(keys[0]) >= 7 else keys[0], calc_base)
    first_label = period_chart_label(keys[0][:7] if calc_base == "monthly" and len(keys[0]) >= 7 else keys[0], calc_base)
    last_label = period_chart_label(keys[-1][:7] if calc_base == "monthly" and len(keys[-1]) >= 7 else keys[-1], calc_base)
    return f"{first_label} a {last_label}"


def infer_view_granularity(calculation_base: str, base_series: list[TimeSeriesPoint]) -> str:
    """Compat: delega para resolve_effective_view_granularity com modo auto."""
    return resolve_effective_view_granularity(calculation_base, base_series, "auto")


def resolve_effective_view_granularity(
    calculation_base: str,
    base_series: list[TimeSeriesPoint],
    explicit: str | None = None,
) -> str:
    """Resolve granularidade efetiva de visualização (auto nunca vira consolidated)."""
    choice = (explicit or "auto").strip().lower()
    if choice == "consolidated":
        return "consolidated"
    if choice and choice != "auto":
        return choice
    if calculation_base == "annual":
        return "annual"
    if len(base_series) >= 2:
        return "monthly"
    if len(base_series) == 1:
        return calculation_base
    return "monthly"


def select_temporal_chart_series(temporal: TemporalModel) -> list[dict[str, Any]]:
    """Série para gráficos de linha — exige >=2 buckets; nunca label de intervalo consolidado."""
    if temporal.view_granularity == "consolidated":
        candidates = temporal.base_series_as_dicts()
    else:
        candidates = [
            p for p in temporal.series_as_dicts()
            if p.get("period_label") != "Período consolidado"
        ]
    if len(candidates) >= 2:
        return candidates
    base = temporal.base_series_as_dicts()
    if len(base) >= 2:
        return base
    return []


def build_temporal_model(
    analysis_cycles: list[dict],
    active_cycle: dict | None = None,
    view_granularity: str | None = None,
    *,
    data_mode: str | None = None,
) -> TemporalModel:
    from utils.calculation_points import build_calculation_points
    from utils.global_filter import filter_cycles_by_data_mode, normalize_data_mode, normalize_view_granularity

    reference = active_cycle or (analysis_cycles[0] if analysis_cycles else {})
    input_gr = infer_input_granularity(reference)
    calc_base = resolve_calculation_base_granularity(input_gr)
    mode = normalize_data_mode(data_mode)
    view_user = normalize_view_granularity(view_granularity)
    filtered = filter_cycles_by_data_mode(analysis_cycles, mode)

    base_series = build_base_series_from_cycles(filtered, calc_base)
    view_gr = resolve_effective_view_granularity(calc_base, base_series, view_user)
    view_series = aggregate_to_view(base_series, view_gr, calc_base)
    calc_points = build_calculation_points(filtered)

    return TemporalModel(
        input_granularity=input_gr,
        calculation_base_granularity=calc_base,
        view_granularity=view_gr,
        view_granularity_user=view_user,
        period_display_label=build_analysis_period_display_label(analysis_cycles, calc_base),
        analysis_period_start=None,
        analysis_period_end=None,
        base_series=base_series,
        view_series=view_series,
        aggregated_approval_status=resolve_aggregated_approval_status(base_series),
        calculation_points=calc_points,
        operational_daily_series=build_operational_daily_series(reference),
        data_mode=mode,
    )


def empty_temporal_model() -> TemporalModel:
    return TemporalModel(
        input_granularity="monthly",
        calculation_base_granularity="monthly",
        view_granularity="monthly",
        view_granularity_user="auto",
        period_display_label="—",
        analysis_period_start=None,
        analysis_period_end=None,
        base_series=[],
        view_series=[],
        aggregated_approval_status=None,
        calculation_points=[],
        data_mode="include_preliminary",
    )
