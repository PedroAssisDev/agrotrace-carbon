"""Detalhamento técnico de emissões por fonte, subcálculos e origem dos dados."""

from __future__ import annotations

from typing import Any

from services.calculation_view_service import (
    build_calculation_parameters,
    build_enteric_tier_comparison,
    build_inputs_summary,
    build_preliminary_result,
    build_subcalculations,
)
from services.cycle_status_service import resolve_managerial_status
from utils.formatting import format_hash_short

_KG_TO_T = 1.0 / 1000.0


def _sub_by_id(cycle: dict) -> dict[str, dict]:
    calc = cycle.get("calculation") or {}
    return {s.get("id"): s for s in (calc.get("subcalculations") or []) if s.get("id")}


def build_overview_cards(
    cycles: list[dict],
    source_ranking: dict[str, Any],
    gas_breakdown: dict[str, Any],
    active_cycle: dict,
) -> list[dict[str, Any]]:
    """Cards principais para a linha de KPIs."""
    from utils.formatting import format_intensity, format_liters, format_t_co2e

    agg_total_t = source_ranking.get("total_t") or 0
    gas_rows = gas_breakdown.get("rows") or []
    prelim = build_preliminary_result(active_cycle)
    st = resolve_managerial_status(active_cycle)

    cards: list[dict[str, Any]] = [
        {
            "title": "Emissões totais",
            "value": format_t_co2e(agg_total_t),
            "subtitle": f"{source_ranking.get('cycle_count', 0)} ciclo(s) no período",
            "icon": "fas fa-cloud",
            "color": "success",
        },
    ]

    for gr in gas_rows:
        pct = gr.get("participacao_pct")
        pct_str = f"{pct:.1f}% do total".replace(".", ",") if pct is not None else ""
        cards.append({
            "title": gr["gas"],
            "value": format_t_co2e(gr.get("co2e_t")),
            "subtitle": pct_str,
            "icon": "fas fa-wind" if gr["gas_key"] == "CH4" else ("fas fa-seedling" if gr["gas_key"] == "N2O" else "fas fa-bolt"),
            "color": "info" if gr["gas_key"] == "CH4" else ("warning" if gr["gas_key"] == "N2O" else "secondary"),
        })

    cards.extend([
        {
            "title": "Intensidade ambiental",
            "value": format_intensity(prelim.get("intensity")),
            "subtitle": "Ciclo ativo",
            "icon": "fas fa-tint",
            "color": "primary",
        },
        {
            "title": "Produção de leite",
            "value": format_liters(prelim.get("milk_production")),
            "subtitle": "Ciclo ativo",
            "icon": "fas fa-glass-whiskey",
            "color": "info",
        },
        {
            "title": "Principal fonte",
            "value": (source_ranking.get("dominant_source") or "—")[:40],
            "subtitle": "Maior emissor no período",
            "icon": "fas fa-industry",
            "color": "danger",
        },
        {
            "title": "Status do cálculo",
            "value": st.label,
            "subtitle": "Preliminar" if not st.is_official else "Oficial",
            "icon": "fas fa-clipboard-check",
            "color": "warning" if not st.is_official else "success",
        },
    ])
    return cards


def build_header_meta(
    active_cycle: dict,
    global_filter: dict | None,
    *,
    consolidated_cycle_count: int,
    has_tier2: bool,
) -> dict[str, Any]:
    """Metadados para cabeçalho e badges."""
    calc = active_cycle.get("calculation") or {}
    st = resolve_managerial_status(active_cycle)
    gf = global_filter or {}

    data_source = calc.get("data_source") or calc.get("source") or "—"
    mode = calc.get("mode") or "—"
    uses_fallback = data_source in {"fallback_defaults", "empty_inputs"} or mode == "mock"

    return {
        "farm_name": active_cycle.get("property_name") or gf.get("farm_name"),
        "period_label": gf.get("period_display_label") or active_cycle.get("reporting_period"),
        "granularity": gf.get("granularity") or gf.get("calculation_base_granularity"),
        "data_mode": gf.get("data_mode", "include_preliminary"),
        "status_label": st.label,
        "is_preliminary": not st.is_official,
        "is_official": st.is_official,
        "data_source": data_source,
        "mode": mode,
        "uses_fallback": uses_fallback,
        "uses_mock": mode == "mock",
        "has_tier2": has_tier2,
        "consolidated_cycle_count": consolidated_cycle_count,
        "cycle_id": active_cycle.get("cycle_id"),
        "reporting_period": active_cycle.get("reporting_period"),
    }


def build_source_details(cycle: dict) -> list[dict[str, Any]]:
    """Detalhamento por fonte emissora (ciclo ativo)."""
    subs = _sub_by_id(cycle)
    calc = cycle.get("calculation") or {}
    inputs = calc.get("inputs") or {}
    factors = calc.get("factors_used") or {}
    gwp = factors.get("gwp") or calc.get("gwp") or {}
    details: list[dict[str, Any]] = []

    enteric = subs.get("enteric", {})
    tier_cmp = build_enteric_tier_comparison(cycle)
    details.append({
        "id": "enteric",
        "title": "Fermentação entérica — CH₄",
        "tier_comparison": tier_cmp,
        "subcalculation": enteric,
        "co2e_t": (enteric.get("co2e_kg") or 0) * _KG_TO_T,
        "inputs": {
            "headcounts": inputs.get("headcounts_by_category"),
            "gwp_ch4": gwp.get("CH4"),
        },
        "factors": enteric.get("factors") or {"enteric_ch4_kg_per_animal": factors.get("enteric_ch4_kg_per_animal")},
    })

    manure = subs.get("manure", {})
    details.append({
        "id": "manure",
        "title": "Manejo de dejetos — CH₄",
        "tier_comparison": None,
        "subcalculation": manure,
        "co2e_t": (manure.get("co2e_kg") or 0) * _KG_TO_T,
        "inputs": {
            "headcounts": inputs.get("headcounts_by_category"),
            "body_weights": inputs.get("body_weight_kg_by_category"),
            "days_in_period": inputs.get("days_in_period") or (calc.get("temporal") or {}).get("days_in_period"),
        },
        "factors": manure.get("factors") or {},
    })

    fertilizer = subs.get("fertilizer", {})
    details.append({
        "id": "fertilizer",
        "title": "Fertilizantes — N₂O",
        "tier_comparison": None,
        "subcalculation": fertilizer,
        "co2e_t": (fertilizer.get("co2e_kg") or 0) * _KG_TO_T,
        "inputs": {"nitrogen_applied_kg": inputs.get("nitrogen_applied_kg")},
        "factors": fertilizer.get("factors") or {"fertilizer_factors": factors.get("fertilizer_factors")},
    })

    energy = subs.get("energy", {})
    details.append({
        "id": "energy",
        "title": "Energia — CO₂",
        "tier_comparison": None,
        "subcalculation": energy,
        "co2e_t": (energy.get("co2e_kg") or 0) * _KG_TO_T,
        "inputs": {"energy_consumption_by_vector": inputs.get("energy_consumption_by_vector")},
        "factors": energy.get("factors") or {"energy_co2_kg_per_unit": factors.get("energy_co2_kg_per_unit")},
    })

    return details


def build_formula_items(cycle: dict) -> list[dict[str, Any]]:
    """Subcálculos com fórmulas para accordion."""
    calc = cycle.get("calculation") or {}
    rows = build_subcalculations(cycle)
    out: list[dict[str, Any]] = []
    for row in rows:
        sub = next((s for s in (calc.get("subcalculations") or []) if s.get("id") == row.get("id")), {})
        out.append({
            **row,
            "co2e_t": (row.get("co2e_kg") or 0) * _KG_TO_T if row.get("co2e_kg") is not None else None,
            "inputs": sub.get("inputs") or {},
            "factors": sub.get("factors") or {},
            "data_source": calc.get("data_source") or calc.get("mode"),
        })
    return out


def build_data_origin_panel(cycle: dict) -> dict[str, Any]:
    """Origem e qualidade dos dados usados no cálculo."""
    calc = cycle.get("calculation") or {}
    raw = cycle.get("raw_file") or {}
    wrapper = cycle.get("wrapper") or {}
    normalized = cycle.get("normalized_data") or wrapper.get("normalized_payload") or []
    input_res = calc.get("input_resolution") or (calc.get("inputs") or {}).get("input_resolution") or []

    found = [r for r in input_res if r.get("status") == "FOUND"]
    missing = [r for r in input_res if r.get("status") == "MISSING_ZERO"]
    defaults = [r for r in input_res if r.get("status") == "DEFAULT_ASSUMED"]

    return {
        "original_filename": raw.get("original_filename"),
        "file_hash": format_hash_short(raw.get("sha256")),
        "normalized_batch_id": cycle.get("normalized_batch_id"),
        "record_count": len(normalized) if isinstance(normalized, list) else 0,
        "variables_found": [r.get("variable") or r.get("slot") for r in found],
        "variables_missing": [r.get("variable") or r.get("slot") for r in missing],
        "variables_default": [r.get("variable") or r.get("slot") for r in defaults],
        "data_source": calc.get("data_source") or calc.get("source"),
        "mode": calc.get("mode"),
        "preliminary_hash": format_hash_short(calc.get("preliminary_hash")),
        "ontology_version": calc.get("ontology_version"),
        "is_fallback": (calc.get("data_source") in {"fallback_defaults", "empty_inputs"}),
        "is_mock": calc.get("mode") == "mock",
        "is_real": calc.get("mode") == "real",
        "inputs_summary": build_inputs_summary(cycle),
        "legacy_schema": not calc.get("input_resolution") and not calc.get("inputs"),
    }


def build_emission_detail_bundle(
    active_cycle: dict,
    work_cycles: list[dict],
    global_filter: dict | None,
    source_ranking: dict[str, Any],
    gas_breakdown: dict[str, Any],
) -> dict[str, Any]:
    """Pacote completo de detalhe para a página."""
    tier = build_enteric_tier_comparison(active_cycle)
    return {
        "header": build_header_meta(
            active_cycle,
            global_filter,
            consolidated_cycle_count=len(work_cycles),
            has_tier2=tier is not None,
        ),
        "overview_cards": build_overview_cards(work_cycles, source_ranking, gas_breakdown, active_cycle),
        "source_details": build_source_details(active_cycle),
        "formulas": build_formula_items(active_cycle),
        "data_origin": build_data_origin_panel(active_cycle),
        "tier_comparison": tier,
        "has_calculation": bool(active_cycle.get("calculation")),
    }
