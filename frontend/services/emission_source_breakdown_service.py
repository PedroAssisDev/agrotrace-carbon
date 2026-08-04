"""Ranking, participação e variações de emissões por fonte."""

from __future__ import annotations

from typing import Any

from services.indicator_aggregation_service import aggregate_emissions, previous_period_delta
from services.indicator_governance_service import source_ranking
from utils.formatting import NA

_KG_TO_T = 1.0 / 1000.0

_SOURCE_GAS_HINT = {
    "Fermentação entérica": "CH₄",
    "Manejo de dejetos": "CH₄",
    "Fertilizantes": "N₂O",
    "Energia": "CO₂",
}


def _gas_hint(source_name: str) -> str:
    for key, gas in _SOURCE_GAS_HINT.items():
        if key.lower() in source_name.lower():
            return gas
    if "CH₄" in source_name or "CH4" in source_name:
        return "CH₄"
    if "N₂O" in source_name or "N2O" in source_name:
        return "N₂O"
    if "CO₂" in source_name or "CO2" in source_name:
        return "CO₂"
    return "—"


def _pct(part: float, total: float) -> float | None:
    if total <= 0:
        return None
    return 100.0 * part / total


def _variation_pct(current: float | None, previous: float | None) -> Any:
    if current is None or previous is None or previous == 0:
        return NA
    return round(100.0 * (current - previous) / abs(previous), 1)


def build_source_ranking(
    cycles: list[dict],
    timeseries: dict[str, Any] | None = None,
    *,
    all_cycles: list[dict] | None = None,
    global_filter: dict | None = None,
) -> dict[str, Any]:
    """Ranking consolidado de fontes emissoras (t CO₂e)."""
    agg = aggregate_emissions(cycles)
    by_source_kg = agg.get("by_source") or {}
    total_kg = float(agg.get("co2e_total_kg") or 0)
    total_t = total_kg * _KG_TO_T

    rows: list[dict[str, Any]] = []
    for src, kg in sorted(by_source_kg.items(), key=lambda x: -float(x[1] or 0)):
        kg_f = float(kg or 0)
        t_val = kg_f * _KG_TO_T
        rows.append({
            "fonte": src,
            "co2e_kg": kg_f,
            "co2e_t": t_val,
            "participacao_pct": _pct(kg_f, total_kg),
            "gas_principal": _gas_hint(src),
            "variacao_pct": NA,
        })

    if timeseries and timeseries.get("has_multi_point"):
        labels = timeseries.get("labels") or []
        by_src_t = timeseries.get("by_source") or {}
        if len(labels) >= 2:
            for row in rows:
                src = row["fonte"]
                vals = by_src_t.get(src) or []
                if len(vals) >= 2 and vals[0] is not None and vals[-1] is not None:
                    row["variacao_pct"] = _variation_pct(vals[-1], vals[0])

    ranking_table = source_ranking(by_source_kg)
    dominant = rows[0]["fonte"] if rows else None

    return {
        "rows": rows,
        "ranking_table": ranking_table,
        "total_t": total_t,
        "total_kg": total_kg,
        "dominant_source": dominant,
        "cycle_count": agg.get("cycle_count", len(cycles)),
    }


def build_gas_breakdown(
    cycles: list[dict],
    timeseries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Quebra consolidada por gás (t CO₂e)."""
    agg = aggregate_emissions(cycles)
    by_gas_kg = agg.get("by_gas") or {}
    total_kg = float(agg.get("co2e_total_kg") or 0)

    gas_sources = {
        "CH4": ["Fermentação entérica", "Manejo de dejetos"],
        "N2O": ["Fertilizantes"],
        "CO2": ["Energia"],
    }

    rows: list[dict[str, Any]] = []
    for gas_key, label in [("CH4", "CH₄"), ("N2O", "N₂O"), ("CO2", "CO₂")]:
        kg = float(by_gas_kg.get(gas_key, 0) or 0)
        t_val = kg * _KG_TO_T
        related = [s for s in (agg.get("by_source") or {}) if any(h in s for h in gas_sources.get(gas_key, []))]
        row: dict[str, Any] = {
            "gas": label,
            "gas_key": gas_key,
            "co2e_kg": kg,
            "co2e_t": t_val,
            "participacao_pct": _pct(kg, total_kg),
            "fontes_relacionadas": ", ".join(related) if related else "—",
            "variacao_pct": NA,
        }
        if timeseries and timeseries.get("has_multi_point"):
            gas_label = {"CH4": "CH₄ (CO₂e)", "N2O": "N₂O (CO₂e)", "CO2": "CO₂"}.get(gas_key, gas_key)
            vals = (timeseries.get("by_gas") or {}).get(gas_label) or []
            if len(vals) >= 2:
                row["variacao_pct"] = _variation_pct(vals[-1], vals[0])
        rows.append(row)

    return {
        "rows": rows,
        "total_t": total_kg * _KG_TO_T,
        "total_kg": total_kg,
    }


def build_variation_summary(
    cycles: list[dict],
    timeseries: dict[str, Any],
    *,
    all_cycles: list[dict] | None = None,
    global_filter: dict | None = None,
) -> dict[str, Any]:
    """Variações percentuais entre período atual e anterior."""
    series_rows = []
    for i, label in enumerate(timeseries.get("labels") or []):
        series_rows.append({
            "period_label": label,
            "co2e_kg": (timeseries.get("total_t") or [None])[i],
            "intensity": (timeseries.get("intensity") or [None])[i],
            "milk_liters": (timeseries.get("milk_liters") or [None])[i],
            "period": label,
        })
        if series_rows[-1]["co2e_kg"] is not None:
            series_rows[-1]["co2e_kg"] = float(series_rows[-1]["co2e_kg"]) * 1000.0

    delta = previous_period_delta(series_rows, all_cycles, global_filter or {})

    items = [
        {"metric": "Emissões totais", "key": "co2e", "variation_pct": delta.get("co2e_pct", NA)},
        {"metric": "Intensidade", "key": "intensity", "variation_pct": delta.get("intensity_pct", NA)},
        {"metric": "Produção de leite", "key": "milk", "variation_pct": delta.get("milk_pct", NA)},
    ]

    src_rank = build_source_ranking(cycles, timeseries)
    for row in src_rank.get("rows") or []:
        items.append({
            "metric": row["fonte"],
            "key": f"source:{row['fonte']}",
            "variation_pct": row.get("variacao_pct", NA),
        })

    gas_bd = build_gas_breakdown(cycles, timeseries)
    for row in gas_bd.get("rows") or []:
        items.append({
            "metric": f"Gás {row['gas']}",
            "key": f"gas:{row['gas_key']}",
            "variation_pct": row.get("variacao_pct", NA),
        })

    return {
        "items": items,
        "has_variation": timeseries.get("has_multi_point", False),
        "delta": delta,
    }
