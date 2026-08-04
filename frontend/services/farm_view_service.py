"""View layer — gestão da fazenda / propriedade."""

from __future__ import annotations

from typing import Any

from services.indicator_service import build_dashboard_indicators
from services.property_registry import load_property_catalog
from utils.global_filter import normalize_global_filter


def build_farm_profile(property_id: str | None, global_filter: dict) -> dict[str, Any]:
    catalog = load_property_catalog()
    gf = normalize_global_filter(global_filter)
    pid = property_id or gf.get("farm_id")
    farm = next((p for p in catalog if p.get("property_id") == pid), catalog[0] if catalog else {})
    return farm or {}


def build_farm_indicators(cycles: list[dict], active_cycle: dict, global_filter: dict, events: list) -> dict[str, Any]:
    ind = build_dashboard_indicators(cycles, active_cycle, global_filter, events, cycles)
    prod = ind.get("productivity") or {}
    em = ind.get("emissions") or {}
    sus = ind.get("sustainability") or {}
    return {
        "production_total": prod.get("total_milk_liters"),
        "production_avg": prod.get("avg_daily_liters"),
        "animals": prod.get("total_animals"),
        "production_per_animal": prod.get("milk_per_animal"),
        "emissions_per_animal": em.get("co2e_per_animal"),
        "kg_co2e_per_liter": em.get("intensity_kg_per_liter"),
        "liters_per_kg_co2e": sus.get("liters_per_kg_co2e"),
        "carbon_productive_efficiency": sus.get("liters_per_kg_co2e"),
        "top_source": em.get("main_source"),
        "variation_pct": prod.get("milk_variation_pct"),
        "best_period": prod.get("best_period"),
        "worst_period": prod.get("worst_period"),
        "liters_per_hectare": prod.get("liters_per_hectare"),
        "alerts": ind.get("alerts") or [],
    }


def build_cycle_history_rows(cycles: list[dict]) -> list[dict]:
    return [{
        "cycle_id": c.get("cycle_id"),
        "period": c.get("reporting_period"),
        "status": c.get("current_status"),
        "co2e_kg": (c.get("calculation") or {}).get("co2e_total_kg"),
        "progress": c.get("current_status"),
    } for c in cycles]
