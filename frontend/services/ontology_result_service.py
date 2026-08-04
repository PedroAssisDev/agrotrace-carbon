"""Persiste resultados de cálculo e observações na ontologia de trabalho."""

from __future__ import annotations

import logging
from typing import Any

from services import ontology_runtime_cache as onto_cache
from services.ontology_adapter import _refresh_cycle_ontology_meta, get_onto_for_cycle

logger = logging.getLogger("agrotrace.ontology_results")

_SUB_TO_SOURCE = {
    "enteric": ("enteric", "CH4", "enteric_fermentation"),
    "manure": ("manure", "CH4", "manure_management"),
    "fertilizer": ("fertilizer", "N2O", "fertilizer_n2o"),
    "energy": ("energy", "CO2", "energy_co2"),
}


def persist_activity_observations(cycle: dict) -> list[dict]:
    """Grava observações de atividade a partir do payload normalizado."""
    from ontology.cycle_model import upsert_emission_cycle, upsert_observation
    from services.domain_catalog import normalize_temporal

    onto = get_onto_for_cycle(cycle)
    cycle_id = str(cycle["cycle_id"])
    property_id = str(cycle.get("property_id") or "UNKNOWN")
    gran = normalize_temporal(cycle.get("granularity") or cycle.get("frequency") or "monthly").value
    upsert_emission_cycle(
        onto,
        cycle_id=cycle_id,
        property_id=property_id,
        reporting_period=str(cycle.get("reporting_period") or ""),
        temporal_granularity=gran,
        property_name=cycle.get("property_name"),
        working_ontology_path=((cycle.get("ontology") or {}).get("export_paths") or {}).get("owl"),
        ontology_version=(cycle.get("ontology") or {}).get("ontology_version"),
    )

    records = cycle.get("normalized_data") or []
    wrapper = cycle.get("wrapper") or {}
    if not records:
        records = wrapper.get("normalized_payload") or []

    applied: list[dict] = []
    skip = {"year", "property_name", "property", "period", "date", "_temporal_context", "period_start", "period_end"}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("variable"):
            var = str(rec["variable"])
            val = rec.get("value", rec.get("valor"))
            if val is None:
                continue
            applied.append(
                upsert_observation(
                    onto,
                    cycle_id=cycle_id,
                    property_id=property_id,
                    variable=var,
                    value=val,
                    unit=rec.get("unit"),
                    status="pending",
                    origin="normalized",
                    period=cycle.get("reporting_period"),
                )
            )
            continue
        for k, v in rec.items():
            if k.startswith("_") or k in skip or not isinstance(v, (int, float)):
                continue
            applied.append(
                upsert_observation(
                    onto,
                    cycle_id=cycle_id,
                    property_id=property_id,
                    variable=str(k),
                    value=v,
                    status="pending",
                    origin="normalized",
                    period=cycle.get("reporting_period"),
                )
            )
    _refresh_cycle_ontology_meta(cycle, onto)
    logger.info("[ONTO] persisted %d observations cycle=%s", len(applied), cycle_id)
    return applied


def persist_calculation_results(
    cycle: dict,
    calculation: dict,
    *,
    status: str = "preliminary",
) -> list[dict]:
    """Persiste EmissionResult a partir do payload de cálculo (após execução pura)."""
    from ontology.result_lifecycle import upsert_emission_result
    from services.domain_catalog import normalize_temporal

    onto = get_onto_for_cycle(cycle)
    cycle_id = str(cycle["cycle_id"])
    property_id = str(cycle.get("property_id") or "UNKNOWN")
    period = str(cycle.get("reporting_period") or calculation.get("reporting_period") or "")
    gran = normalize_temporal(
        (calculation.get("temporal") or {}).get("scope")
        or cycle.get("granularity")
        or cycle.get("frequency")
        or "monthly"
    ).value
    version = (cycle.get("ontology") or {}).get("ontology_version")
    method = calculation.get("method") or {}
    method_id = method.get("code")
    method_version = method.get("version") or calculation.get("calculation_version")

    persisted: list[dict] = []
    for sub in calculation.get("subcalculations") or []:
        sid = sub.get("id") or ""
        src, gas, formula = _SUB_TO_SOURCE.get(sid, (sid, sub.get("gas") or "CO2e", sid))
        persisted.append(
            upsert_emission_result(
                onto,
                cycle_id=cycle_id,
                property_id=property_id,
                reporting_period=period,
                temporal_granularity=gran,
                formula_id=formula,
                gas=str(sub.get("gas") or gas),
                value=float(sub.get("result_kg") or 0),
                unit=str(sub.get("unit") or "kg"),
                co2e_value=float(sub.get("co2e_kg") or 0),
                emission_source=src,
                status=status,
                method_id=method_id,
                method_version=method_version,
                ontology_version=version,
                property_name=cycle.get("property_name"),
            )
        )

    total = calculation.get("co2e_total_kg")
    if total is not None:
        persisted.append(
            upsert_emission_result(
                onto,
                cycle_id=cycle_id,
                property_id=property_id,
                reporting_period=period,
                temporal_granularity=gran,
                formula_id="total_ghg",
                gas="CO2e",
                value=float(total),
                unit="kg CO2e",
                co2e_value=float(total),
                emission_source="total",
                status=status,
                method_id=method_id,
                method_version=method_version,
                ontology_version=version,
                property_name=cycle.get("property_name"),
            )
        )

    intensity = calculation.get("co2e_intensity_per_milk_liter")
    if intensity is not None:
        persisted.append(
            upsert_emission_result(
                onto,
                cycle_id=cycle_id,
                property_id=property_id,
                reporting_period=period,
                temporal_granularity=gran,
                formula_id="intensity",
                gas="CO2e",
                value=float(intensity),
                unit="kg CO2e/L",
                co2e_value=None,
                emission_source="intensity",
                status=status,
                method_id=method_id,
                method_version=method_version,
                ontology_version=version,
                property_name=cycle.get("property_name"),
            )
        )

    _refresh_cycle_ontology_meta(cycle, onto)
    onto_cache.set_ontology(cycle_id, onto)
    cycle["ontology_results"] = {
        "status": status,
        "count": len(persisted),
        "result_keys": [p.get("result_key") for p in persisted],
    }
    logger.info("[ONTO] persisted %d results cycle=%s status=%s", len(persisted), cycle_id, status)
    return persisted


def update_activity_observation(
    cycle: dict,
    *,
    variable: str,
    value: float,
    reviewer: str | None = None,
) -> dict:
    from ontology.cycle_model import upsert_observation

    onto = get_onto_for_cycle(cycle)
    info = upsert_observation(
        onto,
        cycle_id=str(cycle["cycle_id"]),
        property_id=str(cycle.get("property_id") or "UNKNOWN"),
        variable=variable,
        value=value,
        status="corrected",
        origin=f"review:{reviewer or 'unknown'}",
        period=cycle.get("reporting_period"),
    )
    _refresh_cycle_ontology_meta(cycle, onto)
    return info
