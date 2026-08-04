"""Adapter para cálculo de emissões."""

from __future__ import annotations

import logging
from typing import Any

import config
from services import direct_imports as di
from services.mock_data import mock_calculation
from utils.hash_helpers import sha256_dict

logger = logging.getLogger("agrotrace.calculation")


def _extract_records(canonical_dataset: dict) -> tuple[list[dict], str]:
    """Obtém registros normalizados do payload canônico ou wrapper."""
    records = canonical_dataset.get("normalized_payload") or []
    source = "normalized_payload"
    if not records:
        wrapper = canonical_dataset.get("wrapper") or {}
        records = wrapper.get("normalized_payload") or []
        source = "wrapper.normalized_payload" if records else source
    return records, source


def _build_farm_input(normalized_batch: dict, params: dict) -> tuple[Any, str]:
    records, data_source = _extract_records(normalized_batch)
    temporal = params.get("temporal_scope", "MONTHLY")

    headcounts = {
        "Lactating_Cows": 19.0,
        "Dry_Cows": 5.0,
        "Heifers": 22.0,
        "Calves": 5.0,
        "Bulls": 0.0,
    }
    body_weights = {k: 450.0 for k in headcounts}
    milk_liters = 12659.0
    nitrogen = 120.0
    energy = {"Diesel": 500.0, "Electricity_Grid": 1200.0}
    used_records = False

    for rec in records:
        var = str(rec.get("variable", rec.get("variavel", ""))).lower()
        val = float(rec.get("value", rec.get("valor", 0)) or 0)
        if not var:
            continue
        used_records = True
        if "milk" in var or "leite" in var:
            milk_liters = val
        if "lactating" in var or "lactante" in var:
            headcounts["Lactating_Cows"] = val
        if "dry" in var and "cow" in var:
            headcounts["Dry_Cows"] = val
        if "heifer" in var or "novilha" in var:
            headcounts["Heifers"] = val
        if "calf" in var or "bezerro" in var:
            headcounts["Calves"] = val
        if "nitrogen" in var or "nitrogenio" in var or "n2o" in var:
            nitrogen = val
        if "diesel" in var:
            energy["Diesel"] = val
        if "electric" in var or "eletric" in var:
            energy["Electricity_Grid"] = val

    if not used_records:
        data_source = "fallback_defaults"

    scope = di.TemporalScope.MONTHLY if temporal == "MONTHLY" else di.TemporalScope.YEARLY
    days = 30 if scope == di.TemporalScope.MONTHLY else 365

    return di.FarmPeriodInput(
        temporal_scope=scope,
        days_in_period=days,
        headcounts_by_category=headcounts,
        body_weight_kg_by_category=body_weights,
        nitrogen_applied_kg=nitrogen,
        energy_consumption_by_vector=energy,
        milk_liters=milk_liters,
    ), data_source


def _mock(canonical_dataset: dict, params: dict, reason: str | None = None) -> dict[str, Any]:
    out = mock_calculation(canonical_dataset, params)
    out["mode"] = "mock"
    if reason:
        out["fallback_reason"] = reason
    return out


def run_emission_calculation(canonical_dataset: dict, params: dict | None = None) -> dict[str, Any]:
    """Executa cálculo real se disponível."""
    params = params or {}
    if config.USE_MOCK_DATA or not config.USE_DIRECT_FUNCTION_CALLS or di.compute_farm_period_emissions is None:
        return _mock(canonical_dataset, params)

    try:
        gwp = params.get("gwp")
        if gwp is None and di.gwp_ipcc_ar4:
            gwp = di.gwp_ipcc_ar4()
        else:
            gwp = gwp or config.DEFAULT_GWP

        farm_input, data_source = _build_farm_input(canonical_dataset, params)
        from emissions.defaults import default_energy_co2_kg_per_unit_yearly_basis

        energy_factors = {
            k: v
            for k, v in default_energy_co2_kg_per_unit_yearly_basis().items()
            if k in farm_input.energy_consumption_by_vector
        }
        bundle = di.compute_farm_period_emissions(
            farm_input,
            gwp=gwp,
            energy_co2_kg_per_unit=energy_factors,
            auto_prorate_factors=True,
        )
        flat = bundle.to_flat_dict()

        by_source = {
            "Fermentação entérica — CH₄": flat.get("co2e_ch4_enteric_portion_kg", flat.get("ch4_enteric_kg", 0) * gwp["CH4"]),
            "Manejo de dejetos — CH₄": flat.get("co2e_ch4_manure_portion_kg", flat.get("ch4_manure_kg", 0) * gwp["CH4"]),
            "Fertilizantes — N₂O": flat.get("co2e_n2o_portion_kg", flat.get("n2o_fertilizer_kg", 0) * gwp["N2O"]),
            "Energia — CO₂": flat.get("co2_energy_portion_kg", flat.get("co2_energy_kg", 0)),
        }

        result = {
            "source": "real",
            "mode": "real",
            "data_source": data_source,
            "ch4_enteric_kg": flat.get("ch4_enteric_kg", 0),
            "ch4_manure_kg": flat.get("ch4_manure_kg", 0),
            "n2o_fertilizer_kg": flat.get("n2o_fertilizer_kg", 0),
            "co2_energy_kg": flat.get("co2_energy_kg", 0),
            "co2e_total_kg": flat.get("co2e_total_kg", 0),
            "co2e_intensity_per_milk_liter": flat.get("co2e_intensity_per_milk_liter", 0),
            "co2e_per_animal": flat.get("co2e_total_kg", 0) / max(sum(farm_input.headcounts_by_category.values()), 1),
            "methodology": params.get("methodology", "IPCC/IDF-compatible"),
            "calculation_version": "0.3.0",
            "ontology_version": canonical_dataset.get("ontology_version", "agromrv_lite"),
            "gwp": gwp,
            "by_source": by_source,
            "by_gas": {
                "CH4": flat.get("co2e_ch4_portion_kg", 0),
                "N2O": flat.get("co2e_n2o_portion_kg", 0),
                "CO2": flat.get("co2_energy_portion_kg", 0),
            },
            "flat": flat,
        }
        result["preliminary_hash"] = sha256_dict({k: v for k, v in result.items() if k != "flat"})
        return result
    except Exception as exc:
        logger.warning("Cálculo real falhou: %s", exc)
        if not config.ALLOW_MOCK_FALLBACK:
            raise
        return _mock(canonical_dataset, params, reason=str(exc))
