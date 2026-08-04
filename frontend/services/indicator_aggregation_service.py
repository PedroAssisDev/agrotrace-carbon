"""Agregação de indicadores e orquestrador build_dashboard_indicators."""

from __future__ import annotations

from typing import Any

from services.indicator_extraction_service import (
    aggregate_animals_representative,
    aggregate_variable,
    estimate_days_in_period,
    extract_milk_from_cycle,
    extract_text_from_cycle,
    num,
    pct_or_na,
    ratio_or_na,
    round_or_na,
)
from services.indicator_governance_service import (
    audit_counts,
    governance_meta,
    pipeline_counts,
    resolve_period_status_label,
    source_ranking,
)
from services.indicator_quality_service import data_quality_block
from services.ontology_indicator_registry import FEED_VARS
from utils.formatting import NA as _NA
from utils.global_filter import normalize_global_filter, normalize_data_mode
from utils.property_filter import aggregate_by_property, aggregate_calculation_metrics, normalize_property_id
from utils.temporal_series import expand_cycles_period_series
from utils.temporal_model import TemporalModel, build_temporal_model, select_temporal_chart_series


def aggregate_emissions(cycles: list[dict]) -> dict[str, Any]:
    base = aggregate_calculation_metrics(cycles)
    by_gas: dict[str, float] = {}
    ch4_total = n2o_total = co2_total = 0.0
    per_property: dict[str, float] = {}

    for c in cycles:
        calc = c.get("calculation") or {}
        pid = normalize_property_id(c) or "—"
        co2e = num(calc.get("co2e_total_kg")) or 0.0
        per_property[pid] = per_property.get(pid, 0.0) + co2e
        for gas, val in (calc.get("by_gas") or {}).items():
            by_gas[gas] = by_gas.get(gas, 0.0) + float(val or 0)
        ch4_total += (num(calc.get("ch4_enteric_kg")) or 0) + (num(calc.get("ch4_manure_kg")) or 0)
        n2o_total += num(calc.get("n2o_fertilizer_kg")) or 0
        co2_total += num(calc.get("co2_energy_kg")) or 0

    if not by_gas and cycles:
        by_gas = {"CH4": ch4_total, "N2O": n2o_total, "CO2": co2_total}

    return {
        **base,
        "by_gas": by_gas,
        "per_property": per_property,
        "ch4_total_kg": by_gas.get("CH4", ch4_total),
        "n2o_total_kg": by_gas.get("N2O", n2o_total),
        "co2_total_kg": by_gas.get("CO2", co2_total),
    }


def chart_period_series(temporal: TemporalModel | None, cycles: list[dict]) -> list[dict]:
    if temporal is not None:
        chart = select_temporal_chart_series(temporal)
        if chart:
            return chart
        if temporal.view_granularity != "consolidated" and temporal.view_series:
            return temporal.series_as_dicts()
        return temporal.base_series_as_dicts()
    return expand_cycles_period_series(cycles)


def period_series(cycles: list[dict], temporal: TemporalModel | None = None) -> list[dict]:
    return chart_period_series(temporal, cycles)


def pct_range_delta(cur: float | None, first: float | None) -> Any:
    """Variação percentual entre valor final e valor inicial da série filtrada."""
    if cur is None or first is None or first == 0:
        return _NA
    return round(100.0 * (cur - first) / abs(first), 1)


def filter_range_delta(
    series: list[dict],
    all_cycles: list[dict] | None = None,
    global_filter: dict | None = None,
) -> dict[str, Any]:
    """Compara o último ponto da série filtrada com o primeiro (first→last)."""
    _ = all_cycles, global_filter  # assinatura mantida para compatibilidade
    empty = {"milk_pct": _NA, "co2e_pct": _NA, "intensity_pct": _NA, "current": None, "previous": None}
    if not series:
        return empty
    if len(series) < 2:
        return {**empty, "current": series[-1], "previous": None}
    first = series[0]
    last = series[-1]
    return {
        "milk_pct": pct_range_delta(last.get("milk_liters"), first.get("milk_liters")),
        "co2e_pct": pct_range_delta(last.get("co2e_kg"), first.get("co2e_kg")),
        "intensity_pct": pct_range_delta(last.get("intensity"), first.get("intensity")),
        "current": last,
        "previous": first,
    }


def source_delta_by_range(
    by_source_series: dict[str, list],
    *,
    source_names: list[str] | None = None,
) -> dict[str, Any]:
    """Variação first→last por fonte emissora a partir de séries temporais."""
    names = source_names or sorted(by_source_series.keys())
    delta: dict[str, Any] = {}
    for src in names:
        vals = by_source_series.get(src) or []
        if len(vals) < 2:
            delta[src] = _NA
            continue
        delta[src] = pct_range_delta(vals[-1], vals[0])
    return delta


previous_period_delta = filter_range_delta


def classify_environmental(intensities: list[float]) -> tuple[str, str]:
    valid = [i for i in intensities if i is not None and i > 0]
    if not valid:
        return _NA, _NA
    current = valid[-1]
    if len(valid) < 2:
        return "atenção", "estável"
    avg = sum(valid) / len(valid)
    if current <= avg * 0.95:
        perf, trend = "bom", "melhorando"
    elif current >= avg * 1.05:
        perf, trend = "crítico", "piorando"
    else:
        perf, trend = "atenção", "estável"
    if len(valid) >= 2:
        if valid[-1] < valid[-2]:
            trend = "melhorando"
        elif valid[-1] > valid[-2]:
            trend = "piorando"
    return perf, trend


def build_management_block(
    cycles: list[dict],
    *,
    total_milk: float | None,
    total_animals: float | None,
) -> dict[str, Any]:
    pasture = aggregate_variable(cycles, "pasture_area")
    dairy_area = aggregate_variable(cycles, "area_used_for_dairy_activity")
    total_feed = aggregate_variable(cycles, "total_feed_input", mode="sum")
    organic = aggregate_variable(cycles, "organic_fertilizer", mode="sum")
    non_organic = aggregate_variable(cycles, "non_organic_fertilizer", mode="sum")
    grid_kwh = aggregate_variable(cycles, "electricity_grid", mode="sum")
    pv_kwh = aggregate_variable(cycles, "photovoltaic_energy", mode="sum")
    dmi = aggregate_variable(cycles, "dry_matter_intake")
    energy_density = aggregate_variable(cycles, "energy_density")

    fert_total = None
    if organic is not None or non_organic is not None:
        fert_total = (organic or 0) + (non_organic or 0)
    energy_total = None
    if grid_kwh is not None or pv_kwh is not None:
        energy_total = (grid_kwh or 0) + (pv_kwh or 0)

    feed_top: list[dict] = []
    for feed in FEED_VARS:
        if feed == "total_feed_input":
            continue
        val = aggregate_variable(cycles, feed, mode="sum")
        if val is not None and val > 0:
            feed_top.append({"label": feed.replace("_", " ").title(), "value": val})
    feed_top.sort(key=lambda x: x["value"], reverse=True)
    feed_top = feed_top[:5]

    return {
        "pasture_area_ha": round_or_na(pasture, 2),
        "dairy_area_ha": round_or_na(dairy_area, 2),
        "total_feed_input_kg": round_or_na(total_feed, 1),
        "dry_matter_intake": round_or_na(dmi, 2),
        "energy_density": round_or_na(energy_density, 2),
        "organic_fertilizer_kg": round_or_na(organic, 1),
        "non_organic_fertilizer_kg": round_or_na(non_organic, 1),
        "organic_fertilizer_pct": pct_or_na(organic, fert_total),
        "electricity_grid_kwh": round_or_na(grid_kwh, 1),
        "photovoltaic_energy_kwh": round_or_na(pv_kwh, 1),
        "renewable_energy_pct": pct_or_na(pv_kwh, energy_total),
        "animals_per_hectare": ratio_or_na(total_animals, pasture, 2),
        "feed_efficiency": ratio_or_na(total_milk, total_feed, 4),
        "feed_top5": feed_top,
        "predominant_soil_type": extract_text_from_cycle(cycles[-1], "predominant_soil_type") if cycles else _NA,
    }


def build_business_block(
    cycles: list[dict],
    *,
    total_milk: float | None,
    milk_sales: float | None,
    pipeline: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    price = aggregate_variable(cycles, "milk_gross_price")
    employees = aggregate_variable(cycles, "employees_during_the_month")
    sales_base = milk_sales if milk_sales is not None else total_milk
    revenue = (price * sales_base) if price is not None and sales_base is not None else None

    return {
        "milk_gross_price": round_or_na(price, 2),
        "estimated_gross_revenue": round_or_na(revenue, 2),
        "employees_count": int(employees) if employees is not None else _NA,
        "milk_per_employee": ratio_or_na(total_milk, employees, 1),
        "cycles_in_progress": pipeline.get("in_progress", 0),
        "awaiting_approval": pipeline.get("awaiting_approval", 0),
        "cycles_approved": pipeline.get("approved", 0),
        "data_utilization_pct": quality.get("utilization_pct", _NA),
        "semantic_warnings": quality.get("semantic_warnings", 0),
        "information_responsible": extract_text_from_cycle(cycles[-1], "information_responsible") if cycles else _NA,
    }


def build_dashboard_indicators(
    cycles: list[dict],
    active_cycle: dict,
    global_filter: dict,
    provenance_events: list[dict] | None = None,
    all_cycles: list[dict] | None = None,
    temporal: TemporalModel | None = None,
) -> dict:
    from utils.global_filter import filter_cycles_by_data_mode, normalize_view_granularity
    from services.ontology_query_adapter import get_indicators_for_cycles

    all_in_scope = list(cycles)
    data_mode = normalize_data_mode(global_filter.get("data_mode"))
    view_gr = normalize_view_granularity(global_filter.get("view_granularity"))
    filtered = filter_cycles_by_data_mode(all_in_scope, data_mode)
    cycles = filtered
    temporal = temporal or (
        build_temporal_model(cycles, active_cycle, view_gr, data_mode=data_mode) if cycles else None
    )

    onto_ind = get_indicators_for_cycles(cycles) if cycles else {
        "source": "ontology",
        "co2e_total_kg": None,
        "milk_liters": None,
        "intensity": None,
        "animals": None,
        "by_source": {},
        "by_gas": {},
        "timeseries": {"labels": [], "co2e_kg": [], "intensity": [], "milk_liters": [], "has_multi_point": False},
        "cycle_count": 0,
        "summaries": [],
    }

    series = chart_period_series(temporal, cycles)
    ts = onto_ind.get("timeseries") or {}
    if ts.get("labels") and any(v is not None for v in (ts.get("co2e_kg") or [])):
        series = []
        for i, label in enumerate(ts["labels"]):
            series.append({
                "period_label": label,
                "period_key": label,
                "co2e_kg": (ts.get("co2e_kg") or [None])[i] if i < len(ts.get("co2e_kg") or []) else None,
                "milk_liters": (ts.get("milk_liters") or [None])[i] if i < len(ts.get("milk_liters") or []) else None,
                "intensity": (ts.get("intensity") or [None])[i] if i < len(ts.get("intensity") or []) else None,
            })

    operational = [p.to_dict() for p in temporal.operational_daily_series] if temporal else []
    emissions = {
        **aggregate_emissions(cycles),
        "co2e_total_kg": onto_ind.get("co2e_total_kg") if onto_ind.get("co2e_total_kg") is not None else aggregate_emissions(cycles).get("co2e_total_kg"),
        "by_source": onto_ind.get("by_source") or aggregate_emissions(cycles).get("by_source") or {},
        "by_gas": onto_ind.get("by_gas") or aggregate_emissions(cycles).get("by_gas") or {},
    }
    # Prefer ontologia; se vazia (ciclos ainda não migrados), aggregate_emissions como bootstrap transitório
    if onto_ind.get("by_source"):
        emissions["by_source"] = onto_ind["by_source"]
        emissions["co2e_total_kg"] = onto_ind.get("co2e_total_kg")
        emissions["by_gas"] = onto_ind.get("by_gas") or {}
        emissions["ch4_total_kg"] = emissions["by_gas"].get("CH4", 0)
        emissions["n2o_total_kg"] = emissions["by_gas"].get("N2O", 0)
        emissions["co2_total_kg"] = emissions["by_gas"].get("CO2", 0)

    delta = filter_range_delta(series, all_cycles, global_filter)
    emission_ts = {
        **(onto_ind.get("timeseries") or {}),
        "by_source": {},
        "has_multi_point": bool((onto_ind.get("timeseries") or {}).get("has_multi_point")),
        "source": "ontology",
    }
    for s in onto_ind.get("summaries") or []:
        for src, val in (s.get("by_source") or {}).items():
            emission_ts.setdefault("by_source", {}).setdefault(src, []).append(float(val))
    if not emission_ts.get("by_source"):
        from services.emission_timeseries_service import build_emission_timeseries
        emission_ts = build_emission_timeseries(cycles, temporal)

    delta_by_source = source_delta_by_range(
        emission_ts.get("by_source") or {},
        source_names=list(emissions["by_source"].keys()),
    ) if emission_ts.get("has_multi_point") else {}
    pipeline = pipeline_counts(cycles)
    audit = audit_counts(cycles, provenance_events)
    quality = data_quality_block(cycles, lambda c: period_series(c, temporal))

    total_milk = onto_ind.get("milk_liters")
    if total_milk is None:
        total_milk = sum(r["milk_liters"] for r in series if r.get("milk_liters") is not None)
    milk_values = [r["milk_liters"] for r in series if r.get("milk_liters") is not None]
    total_animals = onto_ind.get("animals")
    animals_mode = "ontology" if total_animals is not None else "legacy"
    if total_animals is None:
        total_animals, animals_mode = aggregate_animals_representative(cycles)
    days_in_period, days_mode = estimate_days_in_period(cycles, series)

    intensities = [r["intensity"] for r in series if r.get("intensity") is not None]
    env_perf, env_trend = classify_environmental(intensities)

    by_prop_milk: dict[str, float] = {}
    grouped = aggregate_by_property(cycles)
    for pid, group in grouped.items():
        by_prop_milk[pid] = sum(extract_milk_from_cycle(c) or 0 for c in group)

    best_period = max(series, key=lambda r: r.get("milk_liters") or 0)["period_label"] if milk_values else _NA
    worst_period = min(series, key=lambda r: r.get("milk_liters") or float("inf"))["period_label"] if milk_values else _NA

    main_source = max(emissions["by_source"], key=emissions["by_source"].get) if emissions["by_source"] else _NA
    co2e_total = emissions["co2e_total_kg"]
    # Intensidade oficial: preferir valor ontológico consolidado (já persistido), sem recalcular como fonte
    intensity_consolidated = onto_ind.get("intensity")
    if intensity_consolidated is None:
        intensity_consolidated = (
            round(co2e_total / total_milk, 4) if co2e_total and milk_values and total_milk else _NA
        )

    bio_pct = None
    energy_pct = None
    if emissions["by_gas"]:
        total_gas = sum(emissions["by_gas"].values()) or 1
        bio_pct = round(100 * (emissions["by_gas"].get("CH4", 0) + emissions["by_gas"].get("N2O", 0)) / total_gas, 1)
        energy_pct = round(100 * emissions["by_gas"].get("CO2", 0) / total_gas, 1)

    carbon_productivity = (total_milk / co2e_total) if co2e_total and total_milk else None

    milk_sales = aggregate_variable(cycles, "milk_sales", mode="sum")
    milk_fat = aggregate_variable(cycles, "milk_fat_percentage", mode="avg")
    milk_protein = aggregate_variable(cycles, "milk_protein_percentage", mode="avg")
    pasture = aggregate_variable(cycles, "pasture_area")
    liters_per_ha = (total_milk / pasture) if total_milk and pasture else None
    sales_rate = pct_or_na(milk_sales, total_milk if milk_values else None)
    co2e_per_ha = (co2e_total / pasture) if co2e_total and pasture else None

    avg_daily = round(total_milk / days_in_period, 1) if milk_values and total_milk else _NA
    avg_daily_note = "Estimativa (base mensal)" if days_mode == "estimated_monthly" else ""

    management = build_management_block(
        cycles, total_milk=total_milk if milk_values else None, total_animals=total_animals,
    )
    business = build_business_block(
        cycles,
        total_milk=total_milk if milk_values else None,
        milk_sales=milk_sales,
        pipeline=pipeline,
        quality=quality,
    )

    meta = governance_meta(cycles, all_in_scope, global_filter, temporal, active_cycle)
    meta["total_animals_mode"] = animals_mode
    meta["days_in_period_mode"] = days_mode
    meta["days_in_period"] = days_in_period

    return {
        "meta": meta,
        "summary": {
            "co2e_total_kg": co2e_total,
            "co2e_total_t": round(co2e_total / 1000, 2) if co2e_total else 0,
            "intensity_kg_per_liter": intensity_consolidated,
            "intensity_consolidated_kg_per_l": intensity_consolidated,
            "total_milk_liters": total_milk if milk_values else _NA,
            "period_status_label": resolve_period_status_label(meta, cycles),
            "cycles_in_progress": pipeline["in_progress"],
            "cycles_approved": pipeline["approved"],
            "awaiting_approval": pipeline["awaiting_approval"],
            "packages_anchored": audit["anchored_packages"],
            "divergences": audit["verifications_divergent"],
            "provenance_events": audit["provenance_events"],
            "data_utilization_pct": quality.get("utilization_pct", _NA),
            "main_source": main_source,
            "blockchain_status": "Liberado" if meta.get("blockchain_unlocked") else "Bloqueado",
        },
        "productivity": {
            "total_milk_liters": total_milk if milk_values else _NA,
            "avg_daily_liters": avg_daily,
            "avg_daily_note": avg_daily_note,
            "avg_monthly_liters": round(total_milk / max(len(series), 1), 1) if milk_values else _NA,
            "milk_per_animal": round(total_milk / total_animals, 1) if total_animals and milk_values else _NA,
            "total_animals": int(total_animals) if total_animals else _NA,
            "total_animals_mode": animals_mode,
            "liters_per_lactating_cow": round(total_milk / total_animals, 1) if total_animals and milk_values else _NA,
            "efficiency_per_cycle": round(total_milk / max(len(cycles), 1), 1) if milk_values else _NA,
            "milk_variation_pct": delta["milk_pct"],
            "best_period": best_period,
            "worst_period": worst_period,
            "milk_by_period": [{"label": r["period_label"], "value": r["milk_liters"]} for r in series if r.get("milk_liters")],
            "operational_milk_by_day": [
                {"label": r["period_label"], "value": r["milk_liters"]} for r in operational if r.get("milk_liters")
            ],
            "milk_by_property": [{"label": k, "value": v} for k, v in by_prop_milk.items()],
            "milk_fat_pct": round_or_na(milk_fat, 2),
            "milk_protein_pct": round_or_na(milk_protein, 2),
            "milk_sales_liters": round_or_na(milk_sales, 1),
            "sales_rate_pct": sales_rate,
            "liters_per_hectare": round_or_na(liters_per_ha, 1),
        },
        "emissions": {
            "co2e_total_kg": co2e_total,
            "co2e_total_t": round(co2e_total / 1000, 2) if co2e_total else 0,
            "intensity_kg_per_liter": intensity_consolidated,
            "intensity_consolidated_kg_per_l": intensity_consolidated,
            "co2e_per_animal": round(co2e_total / total_animals, 2) if total_animals and co2e_total else _NA,
            "by_property": emissions["per_property"],
            "ch4_total_kg": emissions["ch4_total_kg"],
            "n2o_total_kg": emissions["n2o_total_kg"],
            "co2_total_kg": emissions["co2_total_kg"],
            "by_source": emissions["by_source"],
            "by_gas": emissions["by_gas"],
            "main_source": main_source,
            "main_source_pct": round(100 * max(emissions["by_source"].values()) / (sum(emissions["by_source"].values()) or 1), 1) if emissions["by_source"] else _NA,
            "co2e_variation_pct": delta["co2e_pct"],
            "intensity_variation_pct": delta["intensity_pct"],
            "co2e_by_period": [{"label": r["period_label"], "value": r["co2e_kg"]} for r in series if r.get("co2e_kg")],
            "co2e_by_period_t": [{"label": r["period_label"], "value": round(r["co2e_kg"] / 1000, 4)} for r in series if r.get("co2e_kg")],
            "intensity_by_period": [{"label": r["period_label"], "value": r["intensity"]} for r in series if r.get("intensity")],
            "period_comparison": {
                "categories": ["Emissões kg CO₂e", "Produção leite", "Intensidade kg CO₂e/L"],
                "current": [
                    delta["current"].get("co2e_kg") if delta.get("current") else None,
                    delta["current"].get("milk_liters") if delta.get("current") else None,
                    delta["current"].get("intensity") if delta.get("current") else None,
                ],
                "previous": [
                    delta["previous"].get("co2e_kg") if delta.get("previous") else None,
                    delta["previous"].get("milk_liters") if delta.get("previous") else None,
                    delta["previous"].get("intensity") if delta.get("previous") else None,
                ],
            },
            "source_ranking": source_ranking(emissions["by_source"], delta_by_source),
        },
        "sustainability": {
            "liters_per_kg_co2e": round(carbon_productivity, 4) if carbon_productivity else _NA,
            "kg_co2e_per_liter": intensity_consolidated or _NA,
            "emissions_by_source_pct": {
                k: round(100 * v / (sum(emissions["by_source"].values()) or 1), 1)
                for k, v in emissions["by_source"].items()
            },
            "biogenic_pct": bio_pct if bio_pct is not None else _NA,
            "energy_pct": energy_pct if energy_pct is not None else _NA,
            "environmental_performance": env_perf,
            "environmental_trend": env_trend,
            "carbon_productivity_series": [
                {"label": r["period_label"],
                 "value": round(r["milk_liters"] / r["co2e_kg"], 6) if r.get("milk_liters") and r.get("co2e_kg") else None}
                for r in series
            ],
            "intensity_series": [{"label": r["period_label"], "value": r["intensity"]} for r in series if r.get("intensity")],
            "efficiency_by_property": [
                {"label": pid, "value": round(v / (emissions["per_property"].get(pid) or 1), 6)}
                for pid, v in by_prop_milk.items() if emissions["per_property"].get(pid)
            ],
            "co2e_per_hectare": round_or_na(co2e_per_ha, 2),
        },
        "management": management,
        "business": business,
        "data_quality": quality,
        "pipeline": pipeline,
        "auditability": audit,
        "series": series,
        "temporal": {
            "input_granularity": temporal.input_granularity if temporal else None,
            "calculation_base_granularity": temporal.calculation_base_granularity if temporal else None,
            "view_granularity": temporal.view_granularity if temporal else None,
            "aggregated_approval_status": temporal.aggregated_approval_status if temporal else None,
            "point_count": len(temporal.view_series) if temporal else 0,
        },
        "active_cycle_id": active_cycle.get("cycle_id"),
    }
