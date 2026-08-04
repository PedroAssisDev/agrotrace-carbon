"""Read model analítico: pontos de cálculo derivados dos ciclos (sem persistência)."""

from __future__ import annotations

from typing import Any

from services.cycle_status_service import resolve_managerial_status
from utils.global_filter import filter_cycles_by_data_mode, normalize_data_mode
from utils.temporal_model import (
    TimeSeriesPoint,
    aggregate_to_view,
    build_base_series_from_cycles,
    infer_input_granularity,
    resolve_calculation_base_granularity,
    resolve_effective_view_granularity,
)


def _point_to_dict(point: TimeSeriesPoint, calc_base: str, input_gr: str) -> dict[str, Any]:
    cycle_id = point.cycle_id or (point.cycle_ids[0] if point.cycle_ids else None)
    is_official = False
    if point.approval_status in ("published", "evidence_generated", "integrity_verified"):
        is_official = True
    return {
        "cycle_id": cycle_id,
        "cycle_ids": point.cycle_ids or ([cycle_id] if cycle_id else []),
        "period": point.period,
        "period_key": point.period_key,
        "period_label": point.period_label,
        "period_start": point.period_start,
        "period_end": point.period_end,
        "input_granularity": input_gr,
        "calculation_base_granularity": calc_base,
        "approval_granularity": calc_base,
        "approval_status": point.approval_status,
        "is_official": is_official,
        "co2e_kg": point.co2e_kg,
        "milk_liters": point.milk_liters,
        "intensity": point.intensity,
    }


def build_calculation_points(cycles: list[dict]) -> list[dict]:
    """Um ponto por unidade-base de cálculo/aprovação."""
    if not cycles:
        return []
    ref = cycles[0]
    input_gr = infer_input_granularity(ref)
    calc_base = resolve_calculation_base_granularity(input_gr)
    series = build_base_series_from_cycles(cycles, calc_base)
    return [_point_to_dict(p, calc_base, input_gr) for p in series]


def filter_calculation_points(points: list[dict], data_mode: str | None) -> list[dict]:
    mode = normalize_data_mode(data_mode)
    if mode in ("all", "include_preliminary"):
        return list(points)
    return [p for p in points if p.get("is_official")]


def aggregate_calculation_points(
    points: list[dict],
    view_granularity: str,
    calc_base: str,
) -> list[dict]:
    """Agrega pontos-base para buckets de visualização."""
    if not points:
        return []
    ts_points = [
        TimeSeriesPoint(
            period=p["period"],
            period_key=p["period_key"],
            period_label=p["period_label"],
            period_start=p.get("period_start"),
            period_end=p.get("period_end"),
            milk_liters=p.get("milk_liters"),
            co2e_kg=p.get("co2e_kg"),
            intensity=p.get("intensity"),
            cycle_id=p.get("cycle_id"),
            approval_status=p.get("approval_status"),
            cycle_ids=p.get("cycle_ids") or [],
        )
        for p in points
    ]
    effective = resolve_effective_view_granularity(calc_base, ts_points, view_granularity)
    aggregated = aggregate_to_view(ts_points, effective, calc_base)
    input_gr = points[0].get("input_granularity", "monthly")
    return [_point_to_dict(p, calc_base, input_gr) for p in aggregated]


def filter_cycles_for_analytics(cycles: list[dict], data_mode: str | None) -> list[dict]:
    """Atalho: filtra ciclos antes de montar pontos."""
    return filter_cycles_by_data_mode(cycles, data_mode)
