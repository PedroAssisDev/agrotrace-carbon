"""Séries temporais de emissões por total, fonte e gás (visualização em t CO₂e)."""

from __future__ import annotations

import re
from typing import Any

from utils.global_filter import cycle_period
from utils.temporal_model import TemporalModel, select_temporal_chart_series
from utils.temporal_series import (
    _cycle_records,
    expand_cycle_temporal_rows,
    expand_cycles_period_series,
    extract_record_period_key,
    resolve_series_granularity,
)

_KG_TO_T = 1.0 / 1000.0
_YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")

_GAS_LABELS = {
    "CH4": "CH₄ (CO₂e)",
    "N2O": "N₂O (CO₂e)",
    "CO2": "CO₂",
}

_SOURCE_ORDER_HINTS = (
    "Fermentação entérica",
    "Manejo de dejetos",
    "Fertilizantes",
    "Energia",
)

_SUB_SOURCE_LABELS = {
    "enteric": "Fermentação entérica — CH₄",
    "manure": "Manejo de dejetos — CH₄",
    "fertilizer": "Fertilizantes — N₂O",
    "energy": "Energia — CO₂",
}

_RECORD_SOURCE_FIELDS = {
    "enteric_tco2e": "Fermentação entérica — CH₄",
    "enteric_co2e_kg": "Fermentação entérica — CH₄",
    "co2e_enteric_kg": "Fermentação entérica — CH₄",
    "manure_tco2e": "Manejo de dejetos — CH₄",
    "manure_ch4_co2e": "Manejo de dejetos — CH₄",
    "fertilizer_n2o_co2e": "Fertilizantes — N₂O",
    "n2o_tco2e": "Fertilizantes — N₂O",
    "energy_co2": "Energia — CO₂",
    "co2_energy_kg": "Energia — CO₂",
    "energy_tco2e": "Energia — CO₂",
}


def _source_sort_key(name: str) -> tuple[int, str]:
    lower = name.lower()
    for idx, hint in enumerate(_SOURCE_ORDER_HINTS):
        if hint.lower() in lower:
            return (idx, name)
    return (len(_SOURCE_ORDER_HINTS), name)


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _kg_to_t(value: float | None) -> float | None:
    if value is None:
        return None
    return value * _KG_TO_T


def _calc_base(temporal: TemporalModel | None) -> str:
    if temporal and temporal.calculation_base_granularity:
        return temporal.calculation_base_granularity
    return "monthly"


def _normalize_period_key(period: str | None, calc_base: str = "monthly") -> str | None:
    if not period:
        return None
    p = str(period).strip()
    if _YEAR_RANGE.match(p):
        return p.split("-")[1] if calc_base == "annual" else p.split("-")[1]
    if len(p) >= 7 and p[4] == "-":
        return p[:7] if calc_base == "monthly" else p[:4]
    if len(p) == 4 and p.isdigit():
        return p
    return p


def _cycle_by_id(cycles: list[dict]) -> dict[str, dict]:
    return {c.get("cycle_id"): c for c in cycles if c.get("cycle_id")}


def _build_cycles_by_period_key(cycles: list[dict], calc_base: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for c in cycles:
        key = _normalize_period_key(cycle_period(c), calc_base)
        if not key:
            continue
        out.setdefault(key, []).append(c)
    return out


def _resolve_chart_rows(cycles: list[dict], temporal: TemporalModel | None) -> list[dict]:
    calc_base = _calc_base(temporal)
    work = [c for c in cycles if (c.get("calculation") or {}).get("co2e_total_kg") is not None]

    if temporal:
        rows = select_temporal_chart_series(temporal)
        if rows:
            return rows
        base = temporal.base_series_as_dicts()
        if base:
            return base
        rows = temporal.series_as_dicts()
        if rows and (rows[0].get("period_label") or "") not in {"Consolidado", "Período consolidado"}:
            return rows

    if len(work) == 1:
        expanded = expand_cycle_temporal_rows(work[0])
        if len(expanded) > 1:
            return expanded

    if work:
        return _rows_from_cycles_direct(work, calc_base)
    return expand_cycles_period_series(cycles)


def _cycle_total_milk(cycle: dict) -> float | None:
    records = _cycle_records(cycle)
    if not records:
        return None
    total = 0.0
    found = False
    for rec in records:
        for key in ("total_milk_production", "milk_production", "milk"):
            v = _num(rec.get(key))
            if v is not None:
                total += v
                found = True
                break
    return total if found else None


def _records_for_period_key(cycle: dict, period_key: str | None, calc_base: str) -> list[dict]:
    if not period_key:
        return []
    granularity = resolve_series_granularity(cycle)
    norm_key = _normalize_period_key(period_key, calc_base) or period_key
    matched: list[dict] = []
    for rec in _cycle_records(cycle):
        rec_key = extract_record_period_key(rec, granularity)
        if not rec_key:
            continue
        rec_norm = _normalize_period_key(rec_key, calc_base) or rec_key
        if rec_key == period_key or rec_norm == norm_key or rec_key == norm_key:
            matched.append(rec)
    return matched


def _extract_by_source_from_records(records: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for rec in records:
        for field, label in _RECORD_SOURCE_FIELDS.items():
            val = _num(rec.get(field))
            if val is not None:
                out[label] = out.get(label, 0.0) + val
    return out


def _prorate_by_source(cycle_sources: dict[str, float], ratio: float) -> dict[str, float]:
    if ratio <= 0 or not cycle_sources:
        return {}
    return {src: float(val or 0) * ratio for src, val in cycle_sources.items()}


def _prorate_by_gas(cycle_gases: dict[str, float], ratio: float) -> dict[str, float]:
    if ratio <= 0 or not cycle_gases:
        return {}
    return {gas: float(val or 0) * ratio for gas, val in cycle_gases.items()}


def _point_ratio(
    row: dict,
    cycle: dict,
    cycle_total_kg: float | None,
) -> float | None:
    """Razão ponto/ciclo para rateio (CO₂e, depois leite). None = usar total do ciclo."""
    point_co2e = _num(row.get("co2e_kg"))
    if point_co2e is not None and cycle_total_kg and cycle_total_kg > 0:
        return point_co2e / cycle_total_kg
    point_milk = _num(row.get("milk_liters"))
    cycle_milk = _cycle_total_milk(cycle)
    if point_milk is not None and cycle_milk and cycle_milk > 0:
        return point_milk / cycle_milk
    return None


def _resolve_point_by_source(
    row: dict,
    cycles: list[dict],
    by_period: dict[str, list[dict]],
    calc_base: str,
) -> dict[str, float]:
    """Resolve by_source para um ponto temporal (ciclo, registros ou rateio).

    Preferência: calculation.by_source / subcalculations do ciclo. Records parciais
    (ex.: só enteric_tco2e) não descartam fontes declaradas no cálculo.
    """
    point_cycles = _cycles_for_point(row, cycles, by_period, calc_base)
    if not point_cycles:
        return {}
    if len(point_cycles) > 1:
        return _aggregate_by_source(point_cycles)

    cycle = point_cycles[0]
    cycle_sources = _calculation_by_source(cycle)
    period_key = row.get("period_key") or row.get("period")
    row_key = _normalize_period_key(str(period_key) if period_key else None, calc_base)
    cycle_key = _normalize_period_key(cycle_period(cycle), calc_base)

    cycle_co2e = _num((cycle.get("calculation") or {}).get("co2e_total_kg"))
    if cycle_co2e is None and cycle_sources:
        cycle_co2e = sum(cycle_sources.values())

    if cycle_sources:
        if row_key and cycle_key and row_key == cycle_key:
            return cycle_sources
        ratio = _point_ratio(row, cycle, cycle_co2e)
        if ratio is not None:
            return _prorate_by_source(cycle_sources, ratio)
        return cycle_sources

    records = _records_for_period_key(cycle, str(period_key or ""), calc_base) if period_key else []
    from_records = _extract_by_source_from_records(records)
    if from_records:
        return from_records
    return {}


def _point_by_gas(point_sources: dict[str, float]) -> dict[str, float]:
    if not point_sources:
        return {}
    out = {"CH4": 0.0, "N2O": 0.0, "CO2": 0.0}
    for label, kg in point_sources.items():
        lower = label.lower()
        if "fertilizante" in lower or "n₂o" in lower or "n2o" in lower:
            out["N2O"] += kg
        elif "energia" in lower:
            out["CO2"] += kg
        else:
            out["CH4"] += kg
    return {k: v for k, v in out.items() if v > 0}


def _resolve_point_by_gas(
    row: dict,
    cycles: list[dict],
    by_period: dict[str, list[dict]],
    calc_base: str,
    point_sources: dict[str, float] | None = None,
) -> dict[str, float]:
    """Resolve by_gas para um ponto: calculation.by_gas primeiro; fallback por fonte.

    Preserva gases declarados no ciclo (CH4/N2O/CO2 e chaves desconhecidas).
    Não inventa valores: rateia o mapa existente ou infere só a partir de fontes.
    """
    point_cycles = _cycles_for_point(row, cycles, by_period, calc_base)
    if not point_cycles:
        return _point_by_gas(point_sources or {})

    if len(point_cycles) > 1:
        return _aggregate_by_gas(point_cycles)

    cycle = point_cycles[0]
    cycle_gases = _calculation_by_gas(cycle)
    period_key = row.get("period_key") or row.get("period")
    row_key = _normalize_period_key(str(period_key) if period_key else None, calc_base)
    cycle_key = _normalize_period_key(cycle_period(cycle), calc_base)

    cycle_co2e = _num((cycle.get("calculation") or {}).get("co2e_total_kg"))
    if cycle_co2e is None and cycle_gases:
        cycle_co2e = sum(cycle_gases.values())

    if cycle_gases:
        if row_key and cycle_key and row_key == cycle_key:
            return cycle_gases
        ratio = _point_ratio(row, cycle, cycle_co2e)
        if ratio is not None:
            return _prorate_by_gas(cycle_gases, ratio)
        return cycle_gases

    src = point_sources if point_sources is not None else _resolve_point_by_source(
        row, cycles, by_period, calc_base,
    )
    return _point_by_gas(src)


def _cycles_for_point(
    point: dict,
    cycles: list[dict],
    by_period: dict[str, list[dict]],
    calc_base: str,
) -> list[dict]:
    """Resolve ciclos para um ponto temporal — cycle_ids, period_key ou mapa direto."""
    by_id = _cycle_by_id(cycles)
    ids = point.get("cycle_ids") or []
    if not ids and point.get("cycle_id"):
        ids = [point["cycle_id"]]
    matched = [by_id[cid] for cid in ids if cid in by_id]
    if matched:
        return matched

    for field in ("period_key", "period"):
        raw = point.get(field)
        if not raw:
            continue
        if raw in by_period:
            return by_period[raw]
        norm = _normalize_period_key(str(raw), calc_base)
        if norm and norm in by_period:
            return by_period[norm]

    period = point.get("period") or point.get("period_key")
    if period:
        norm = _normalize_period_key(str(period), calc_base)
        if norm and norm in by_period:
            return by_period[norm]
        return [
            c for c in cycles
            if (cycle_period(c) or "") == str(period)
            or str(cycle_period(c) or "").startswith(str(period))
            or (norm and _normalize_period_key(cycle_period(c), calc_base) == norm)
        ]
    return []


def _aggregate_by_gas(cycle_list: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in cycle_list:
        for gas, val in _calculation_by_gas(c).items():
            out[gas] = out.get(gas, 0.0) + float(val or 0)
    return out


def _calculation_by_source(cycle: dict) -> dict[str, float]:
    """by_source do ciclo, com fallback por subcálculos ou campos legados."""
    calc = cycle.get("calculation") or {}
    raw = calc.get("by_source") or {}
    if raw:
        return {str(k): float(v or 0) for k, v in raw.items()}

    out: dict[str, float] = {}
    for sub in calc.get("subcalculations") or []:
        sid = sub.get("id")
        label = _SUB_SOURCE_LABELS.get(sid)
        if label and sub.get("co2e_kg") is not None:
            out[label] = float(sub.get("co2e_kg") or 0)
    if out:
        return out

    flat = calc.get("flat") or {}
    legacy = {
        "Fermentação entérica — CH₄": float(
            calc.get("enteric_ch4_co2e") or flat.get("co2e_ch4_portion_kg") or calc.get("ch4_enteric_kg") or 0
        ),
        "Manejo de dejetos — CH₄": float(calc.get("manure_ch4_co2e") or 0),
        "Fertilizantes — N₂O": float(calc.get("fertilizer_n2o_co2e") or flat.get("co2e_n2o_portion_kg") or 0),
        "Energia — CO₂": float(calc.get("energy_co2") or flat.get("co2_energy_portion_kg") or 0),
    }
    if any(v > 0 for v in legacy.values()):
        return legacy
    return out


def _calculation_by_gas(cycle: dict) -> dict[str, float]:
    calc = cycle.get("calculation") or {}
    raw = calc.get("by_gas") or {}
    if raw:
        return {str(k): float(v or 0) for k, v in raw.items()}

    src = _calculation_by_source(cycle)
    if not src:
        return {}

    out = {"CH4": 0.0, "N2O": 0.0, "CO2": 0.0}
    for label, kg in src.items():
        lower = label.lower()
        if "fertilizante" in lower or "n₂o" in lower or "n2o" in lower:
            out["N2O"] += kg
        elif "energia" in lower:
            out["CO2"] += kg
        else:
            out["CH4"] += kg
    return {k: v for k, v in out.items() if v > 0}


def _aggregate_by_source(cycle_list: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in cycle_list:
        for src, val in _calculation_by_source(c).items():
            out[src] = out.get(src, 0.0) + float(val or 0)
    return out


def _rows_from_cycles_direct(work: list[dict], calc_base: str) -> list[dict]:
    """Fallback: uma linha por ciclo ordenado por período."""
    from utils.temporal_series import period_chart_label

    rows: list[dict] = []
    for c in sorted(work, key=lambda x: cycle_period(x) or ""):
        period = cycle_period(c) or ""
        key = _normalize_period_key(period, calc_base) or period
        calc = c.get("calculation") or {}
        milk = None
        wrapper = c.get("wrapper") or {}
        payload = wrapper.get("normalized_payload") or c.get("normalized_data") or []
        if isinstance(payload, list) and payload:
            for rec in payload:
                if isinstance(rec, dict):
                    milk = _num(rec.get("milk_production") or rec.get("total_milk_production"))
                    if milk is not None:
                        break
        co2e = _num(calc.get("co2e_total_kg"))
        intensity = _num(calc.get("co2e_intensity_per_milk_liter"))
        if intensity is None and co2e and milk and milk > 0:
            intensity = co2e / milk
        rows.append({
            "period": period,
            "period_key": key,
            "period_label": period_chart_label(key, calc_base),
            "co2e_kg": co2e,
            "intensity": intensity,
            "milk_liters": milk,
            "cycle_id": c.get("cycle_id"),
            "cycle_ids": [c.get("cycle_id")] if c.get("cycle_id") else [],
        })
    return rows


def _build_series_from_rows(
    rows: list[dict],
    work: list[dict],
    by_period: dict[str, list[dict]],
    calc_base: str,
) -> tuple[list[str], list[float | None], list[float | None], list[float | None], list[dict[str, float]], list[dict[str, float]]]:
    labels: list[str] = []
    total_t: list[float | None] = []
    intensity: list[float | None] = []
    milk_liters: list[float | None] = []
    point_sources: list[dict[str, float]] = []
    point_gases: list[dict[str, float]] = []

    for row in rows:
        labels.append(row.get("period_label") or row.get("period_key") or row.get("period") or "—")
        total_t.append(_kg_to_t(_num(row.get("co2e_kg"))))
        intensity.append(_num(row.get("intensity")))
        milk_liters.append(_num(row.get("milk_liters")))
        src = _resolve_point_by_source(row, work, by_period, calc_base)
        point_sources.append(src)
        point_gases.append(
            _resolve_point_by_gas(row, work, by_period, calc_base, point_sources=src)
        )

    return labels, total_t, intensity, milk_liters, point_sources, point_gases


def build_source_line_series(
    cycles: list[dict],
    temporal: TemporalModel | None = None,
) -> tuple[list[str], dict[str, list[float | None]]]:
    """Série temporal por fonte — alinhada ao modelo temporal (mensal quando disponível)."""
    work = [c for c in cycles if (c.get("calculation") or {}).get("co2e_total_kg") is not None]
    if not work:
        return [], {}

    calc_base = _calc_base(temporal)
    by_period = _build_cycles_by_period_key(work, calc_base)
    rows = _resolve_chart_rows(work, temporal)
    labels, _, _, _, point_sources, _ = _build_series_from_rows(rows, work, by_period, calc_base)

    all_sources = sorted({k for ps in point_sources for k in ps}, key=_source_sort_key)
    by_source: dict[str, list[float | None]] = {
        src: [_kg_to_t(ps.get(src)) for ps in point_sources] for src in all_sources
    }
    return labels, by_source


def build_consolidated_source_from_ranking(ranking: dict) -> tuple[list[str], dict[str, list[float | None]]]:
    """Fallback: 1 ponto consolidado a partir do ranking de fontes (kg → t)."""
    rows = ranking.get("rows") or []
    if not rows:
        return [], {}
    by_source: dict[str, list[float | None]] = {}
    for row in rows:
        fonte = row.get("fonte")
        kg = row.get("co2e_kg")
        if fonte and kg is not None:
            by_source[str(fonte)] = [_kg_to_t(float(kg))]
    return ["Consolidado"], by_source


def build_emission_timeseries(
    cycles: list[dict],
    temporal: TemporalModel | None = None,
) -> dict[str, Any]:
    """Monta séries temporais consolidadas para a tela de Cálculos de Emissão."""
    work = [c for c in cycles if (c.get("calculation") or {}).get("co2e_total_kg") is not None]
    if not work:
        return {
            "labels": [],
            "total_t": [],
            "intensity": [],
            "milk_liters": [],
            "by_source": {},
            "by_gas": {},
            "point_count": 0,
            "has_series": False,
        }

    calc_base = _calc_base(temporal)
    by_period = _build_cycles_by_period_key(work, calc_base)
    rows = _resolve_chart_rows(work, temporal)

    labels, total_t, intensity, milk_liters, point_sources, point_gases = _build_series_from_rows(
        rows, work, by_period, calc_base,
    )

    all_sources = sorted({k for ps in point_sources for k in ps}, key=_source_sort_key)
    all_gases = sorted({k for pg in point_gases for k in pg})
    by_source: dict[str, list[float | None]] = {
        src: [_kg_to_t(ps.get(src)) for ps in point_sources] for src in all_sources
    }
    by_gas: dict[str, list[float | None]] = {
        gas: [_kg_to_t(pg.get(gas)) for pg in point_gases] for gas in all_gases
    }
    by_gas_labeled = {_GAS_LABELS.get(k, k): v for k, v in by_gas.items()}

    return {
        "labels": labels,
        "total_t": total_t,
        "intensity": intensity,
        "milk_liters": milk_liters,
        "by_source": by_source,
        "by_gas": by_gas_labeled,
        "by_gas_raw": by_gas,
        "point_count": len(labels),
        "has_series": len(labels) >= 1,
        "has_multi_point": len(labels) >= 2,
    }


def build_per_source_temporal_charts(timeseries: dict[str, Any]) -> list[dict[str, Any]]:
    """Uma entrada por fonte emissora para gráficos individuais de evolução."""
    labels = timeseries.get("labels") or []
    by_source = timeseries.get("by_source") or {}
    charts: list[dict[str, Any]] = []
    for src in sorted(by_source.keys(), key=_source_sort_key):
        values = by_source[src]
        charts.append({
            "source": src,
            "labels": labels,
            "values_t": values,
            "title": f"{src} — evolução (t CO₂e)",
        })
    return charts


def build_per_gas_temporal_charts(timeseries: dict[str, Any]) -> list[dict[str, Any]]:
    labels = timeseries.get("labels") or []
    charts: list[dict[str, Any]] = []
    for gas, values in (timeseries.get("by_gas") or {}).items():
        charts.append({
            "gas": gas,
            "labels": labels,
            "values_t": values,
            "title": f"{gas} — evolução (t CO₂e)",
        })
    return charts
