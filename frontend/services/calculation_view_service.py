"""View layer — cálculos, aprovação e publicação final."""

from __future__ import annotations

from typing import Any

import config
from services.blockchain_view_service import is_blockchain_unlocked


def build_preliminary_result(cycle: dict) -> dict[str, Any]:
    c = cycle.get("calculation") or {}
    return {
        "co2e_total_kg": c.get("co2e_total_kg"),
        "co2e_total_t": (c.get("co2e_total_kg") or 0) / 1000 if c.get("co2e_total_kg") else None,
        "intensity": c.get("co2e_intensity_per_milk_liter"),
        "milk_production": c.get("milk_production_l"),
        "ch4_kg": c.get("ch4_kg"),
        "n2o_kg": c.get("n2o_kg"),
        "co2_kg": c.get("co2_kg"),
        "status": (cycle.get("steps") or {}).get("approval", {}).get("status", "AWAITING_APPROVAL"),
        "hash": c.get("result_hash"),
        "mode": c.get("mode") or c.get("source"),
    }


def build_calculation_parameters(cycle: dict) -> dict[str, Any]:
    c = cycle.get("calculation") or {}
    ont = cycle.get("ontology") or {}
    return {
        "methodology": c.get("methodology", "IPCC / GEE agropecuário"),
        "calculation_version": c.get("version", "—"),
        "gwp": config.DEFAULT_GWP,
        "factors": c.get("factors_used") or [],
        "canonical_version": ont.get("ontology_version"),
        "inputs_summary": c.get("inputs_summary", "Dados normalizados do ciclo"),
    }


def build_source_breakdown(cycle: dict) -> list[dict]:
    c = cycle.get("calculation") or {}
    by_source = c.get("by_source") or {}
    if not by_source and c.get("co2e_total_kg"):
        by_source = {
            "Fermentação entérica": c.get("enteric_ch4_co2e", 0),
            "Manejo de dejetos": c.get("manure_ch4_co2e", 0),
            "Fertilizantes": c.get("fertilizer_n2o_co2e", 0),
            "Energia": c.get("energy_co2", 0),
        }
    return [{"fonte": k, "co2e_kg": v} for k, v in by_source.items()]


def build_approval_view(cycle: dict) -> dict[str, Any]:
    a = cycle.get("approval") or {}
    step = (cycle.get("steps") or {}).get("approval", {})
    return {
        "decision": a.get("decision") or step.get("status"),
        "approver": a.get("approver"),
        "justification": a.get("justification"),
        "approved_at": a.get("approved_at"),
        "hash": a.get("approval_hash"),
        "mode": step.get("mode"),
    }


def build_publication_view(cycle: dict) -> dict[str, Any]:
    pub = cycle.get("publication") or {}
    return {
        "ontology_version": pub.get("ontology_version"),
        "ontology_hash": pub.get("ontology_hash"),
        "published_at": pub.get("published_at"),
        "blockchain_unlocked": is_blockchain_unlocked(cycle),
        "status": (cycle.get("steps") or {}).get("publication", {}).get("status"),
    }
