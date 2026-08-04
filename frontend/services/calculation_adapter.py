"""Adapter para cálculo de emissões."""

from __future__ import annotations

import logging
from typing import Any

import config
from services import direct_imports as di
from services.mock_data import mock_calculation
from utils.hash_helpers import sha256_dict

logger = logging.getLogger("agrotrace.calculation")

# Catálogo de fórmulas (texto fixo para auditoria na UI)
_FORMULAS: dict[str, str] = {
    "enteric": "Σ(headcount[categoria] × ef_enteric[categoria])",
    "manure": "Σ(n × peso × ef_esterco/dia × ef_CH4/esterco × dias)",
    "fertilizer": "N × ef_direto + N × fração_volatilizada × ef_indireto",
    "energy": "Σ(consumo[vetor] × ef_CO2[vetor])",
    "total": "CH4_total × GWP_CH4 + N2O × GWP_N2O + CO2",
    "intensity_liter": "CO2e_total / litros_leite",
    "intensity_fpcm": "CO2e_total / kg_FPCM",
}


def _extract_records(canonical_dataset: dict) -> tuple[list[dict], str]:
    """Obtém registros normalizados do payload canônico ou wrapper."""
    records = canonical_dataset.get("normalized_data") or canonical_dataset.get("normalized_payload") or []
    source = "normalized_data" if canonical_dataset.get("normalized_data") else "normalized_payload"
    if not records:
        wrapper = canonical_dataset.get("wrapper") or {}
        records = wrapper.get("normalized_payload") or []
        source = "wrapper.normalized_payload" if records else source
    return records, source


def _row_float(row: dict, *keys: str) -> float | None:
    total = 0.0
    found = False
    for key in keys:
        if key not in row or row[key] is None or row[key] == "":
            continue
        try:
            total += float(row[key])
            found = True
        except (TypeError, ValueError):
            continue
    return total if found else None


def _row_first_float(row: dict, *keys: str) -> tuple[float | None, str | None]:
    for key in keys:
        if key not in row or row[key] is None or row[key] == "":
            continue
        try:
            return float(row[key]), key
        except (TypeError, ValueError):
            continue
    return None, None


def _row_period_key(row: dict) -> str | None:
    temporal = row.get("_temporal_context") or {}
    start = temporal.get("start") or row.get("period_start")
    if isinstance(start, str) and len(start) >= 7:
        return start[:7]
    return None


def _select_ecofarm_row(records: list[dict], reporting_period: str | None) -> dict | None:
    if not records:
        return None
    columnar = [r for r in records if isinstance(r, dict) and not r.get("variable") and not r.get("variavel")]
    if not columnar:
        return records[0] if records else None
    if reporting_period and len(reporting_period) >= 7:
        matched = [r for r in columnar if _row_period_key(r) == reporting_period[:7]]
        if matched:
            return matched[0]
    return columnar[0]


_DEFAULT_BODY_WEIGHT_KG = 450.0

# Mapeamento agregado ECOFARM → slots legados FarmPeriodInput (documentado no relatório)
_ECOFARM_HEADCOUNT_FIRST: list[tuple[str, tuple[str, ...]]] = [
    ("Lactating_Cows", ("lactating_cows", "number_of_lactating_cows")),
    ("Dry_Cows", ("dry_cows", "number_of_dry_cows")),
]

_ECOFARM_HEADCOUNT_SUM: list[tuple[str, tuple[str, ...]]] = [
    ("Heifers", ("heifers_in_raising", "pregnant_heifers", "heifers")),
    ("Calves", (
        "suckling_calves_female", "suckling_calves_male",
        "male_calves_in_raising", "male_calves_in_fattening", "calves",
    )),
    ("Bulls", ("reproducers", "draft_and_breeding_bulls", "bulls")),
]

_ECOFARM_ENERGY_MAP: list[tuple[str, tuple[str, ...]]] = [
    ("Diesel", ("diesel", "Diesel")),
    ("Gasoline", ("gasoline", "Gasoline")),
    ("Electricity_Grid", ("electricity_grid", "Electricity_Grid", "electricity")),
    ("Photovoltaic_Energy", ("photovoltaic_energy", "Photovoltaic_Energy", "photovoltaic")),
]


def _resolution_entry(
    slot: str,
    variable: str,
    value: float | None,
    *,
    unit: str,
    status: str,
    source: str = "normalized_data",
) -> dict[str, Any]:
    return {
        "slot": slot,
        "variable": variable,
        "value": value if value is not None else 0.0,
        "unit": unit,
        "status": status,
        "source": source,
    }


def _apply_ecofarm_row(
    row: dict,
    *,
    locked: set[str],
    headcounts: dict[str, float],
    body_weights: dict[str, float],
    milk_liters: float,
    nitrogen: float,
    energy: dict[str, float],
    input_resolution: list[dict[str, Any]],
) -> tuple[bool, float, float]:
    """Aplica mapeamento colunar ECOFARM; retorna (used, milk_liters, nitrogen)."""
    if not row or (row.get("variable") or row.get("variavel")):
        return False, milk_liters, nitrogen

    used = False
    if "headcounts" not in locked:
        for category, columns in _ECOFARM_HEADCOUNT_FIRST:
            val, col = _row_first_float(row, *columns)
            if val is not None:
                headcounts[category] = val
                used = True
                input_resolution.append(_resolution_entry(
                    f"headcount:{category}",
                    col or columns[0],
                    val,
                    unit="head",
                    status="FOUND",
                ))
        for category, columns in _ECOFARM_HEADCOUNT_SUM:
            val = _row_float(row, *columns)
            if val is not None:
                headcounts[category] = val
                used = True
                input_resolution.append(_resolution_entry(
                    f"headcount:{category}",
                    "+".join(columns) if len(columns) > 1 else columns[0],
                    val,
                    unit="head",
                    status="FOUND",
                ))
        for category in headcounts:
            weight_key = f"{category}_Weight"
            weight_val = _row_float(row, weight_key.lower(), f"{category.lower()}_weight")
            if weight_val is not None:
                body_weights[category] = weight_val
                input_resolution.append(_resolution_entry(
                    f"body_weight:{category}",
                    weight_key,
                    weight_val,
                    unit="kg",
                    status="FOUND",
                ))
            else:
                body_weights.setdefault(category, _DEFAULT_BODY_WEIGHT_KG)
                input_resolution.append(_resolution_entry(
                    f"body_weight:{category}",
                    f"{category}_Weight (default)",
                    _DEFAULT_BODY_WEIGHT_KG,
                    unit="kg",
                    status="DEFAULT_ASSUMED",
                ))

    if "milk" not in locked:
        milk_val = _row_float(row, "milk_production", "milk_sales", "Milk_Liters", "milk")
        if milk_val is not None:
            milk_liters = milk_val
            used = True
            input_resolution.append(_resolution_entry(
                "milk_liters",
                "milk_production",
                milk_val,
                unit="L",
                status="FOUND",
            ))

    if "nitrogen" not in locked:
        n_val = _row_float(row, "non_organic_fertilizer", "Non_Organic_Fertilizer", "nitrogen_applied")
        if n_val is not None:
            nitrogen = n_val
            used = True
            input_resolution.append(_resolution_entry(
                "nitrogen_applied_kg",
                "non_organic_fertilizer",
                n_val,
                unit="kg N",
                status="FOUND",
            ))
        else:
            input_resolution.append(_resolution_entry(
                "nitrogen_applied_kg",
                "non_organic_fertilizer",
                0.0,
                unit="kg N",
                status="MISSING_ZERO",
            ))

    if "energy" not in locked:
        for vector, columns in _ECOFARM_ENERGY_MAP:
            e_val = _row_float(row, *columns)
            if e_val is not None:
                energy[vector] = e_val
                used = True
                input_resolution.append(_resolution_entry(
                    f"energy:{vector}",
                    columns[0],
                    e_val,
                    unit="L" if vector in {"Diesel", "Gasoline"} else "kWh",
                    status="FOUND",
                ))
            else:
                energy.setdefault(vector, 0.0)
                input_resolution.append(_resolution_entry(
                    f"energy:{vector}",
                    columns[0],
                    0.0,
                    unit="L" if vector in {"Diesel", "Gasoline"} else "kWh",
                    status="MISSING_ZERO",
                ))

    return used, milk_liters, nitrogen


def _build_farm_input(normalized_batch: dict, params: dict) -> tuple[Any, dict[str, Any], str, list[dict[str, Any]]]:
    """Retorna (FarmPeriodInput, inputs_dict, data_source, input_resolution)."""
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
    input_resolution: list[dict[str, Any]] = []

    # input_overrides tem prioridade sobre normalized_data e defaults
    overrides = params.get("input_overrides") or {}
    locked: set[str] = set()
    if overrides.get("headcounts_by_category"):
        headcounts.update({k: float(v) for k, v in overrides["headcounts_by_category"].items()})
        locked.add("headcounts")
        used_records = True
    if overrides.get("body_weight_kg_by_category"):
        body_weights.update({k: float(v) for k, v in overrides["body_weight_kg_by_category"].items()})
        locked.add("body_weights")
        used_records = True
    if overrides.get("milk_liters") is not None:
        milk_liters = float(overrides["milk_liters"])
        locked.add("milk")
        used_records = True
    if overrides.get("nitrogen_applied_kg") is not None:
        nitrogen = float(overrides["nitrogen_applied_kg"])
        locked.add("nitrogen")
        used_records = True
    if overrides.get("energy_consumption_by_vector"):
        energy.update({k: float(v) for k, v in overrides["energy_consumption_by_vector"].items()})
        locked.add("energy")
        used_records = True

    reporting_period = (
        normalized_batch.get("reporting_period")
        or (normalized_batch.get("wrapper") or {}).get("reporting_period")
    )
    ecofarm_row = _select_ecofarm_row(records, reporting_period)
    if ecofarm_row:
        ecofarm_used, milk_liters, nitrogen = _apply_ecofarm_row(
            ecofarm_row,
            locked=locked,
            headcounts=headcounts,
            body_weights=body_weights,
            milk_liters=milk_liters,
            nitrogen=nitrogen,
            energy=energy,
            input_resolution=input_resolution,
        )
        if ecofarm_used:
            used_records = True
            data_source = "normalized_data"

    for rec in records:
        var = str(rec.get("variable", rec.get("variavel", ""))).lower()
        val = float(rec.get("value", rec.get("valor", 0)) or 0)
        if not var:
            continue
        used_records = True
        if "milk" not in locked and ("milk" in var or "leite" in var):
            milk_liters = val
        if "headcounts" not in locked:
            if "lactating" in var or "lactante" in var:
                headcounts["Lactating_Cows"] = val
            if "dry" in var and "cow" in var:
                headcounts["Dry_Cows"] = val
            if "heifer" in var or "novilha" in var:
                headcounts["Heifers"] = val
            if "calf" in var or "bezerro" in var:
                headcounts["Calves"] = val
        if "nitrogen" not in locked and ("nitrogen" in var or "nitrogenio" in var or "n2o" in var):
            nitrogen = val
        if "energy" not in locked:
            if "diesel" in var:
                energy["Diesel"] = val
            if "electric" in var or "eletric" in var:
                energy["Electricity_Grid"] = val

    if not used_records:
        data_source = "fallback_defaults"

    scope = di.TemporalScope.MONTHLY if temporal == "MONTHLY" else di.TemporalScope.YEARLY
    days = int(params.get("days_in_period") or (30 if scope == di.TemporalScope.MONTHLY else 365))

    inputs = {
        "headcounts_by_category": dict(headcounts),
        "body_weight_kg_by_category": dict(body_weights),
        "nitrogen_applied_kg": nitrogen,
        "energy_consumption_by_vector": dict(energy),
        "milk_liters": milk_liters,
        "milk_kg_fpcm": params.get("milk_kg_fpcm"),
        "input_resolution": input_resolution,
    }

    farm_input = di.FarmPeriodInput(
        temporal_scope=scope,
        days_in_period=days,
        headcounts_by_category=headcounts,
        body_weight_kg_by_category=body_weights,
        nitrogen_applied_kg=nitrogen,
        energy_consumption_by_vector=energy,
        milk_liters=milk_liters,
    )
    return farm_input, inputs, data_source, input_resolution


def _resolve_factors(params: dict, farm_input: Any) -> dict[str, Any]:
    """Resolve os 5 grupos de fatores + GWP a partir de params ou defaults."""
    from emissions.defaults import (
        default_energy_co2_kg_per_unit_yearly_basis,
        default_enteric_ch4_kg_per_animal_yearly,
        default_fertilizer_factors,
        default_manure_ch4_kg_per_kg_manure,
        default_manure_kg_per_kg_bw_per_day,
    )
    from emissions.factor_alignment import (
        align_energy_factors_to_scope,
        align_enteric_factors_to_scope,
    )

    auto_prorate = params.get("auto_prorate_factors", True)
    scope = farm_input.temporal_scope

    raw_enteric = params.get("enteric_ch4_kg_per_animal") or default_enteric_ch4_kg_per_animal_yearly()
    if params.get("enteric_ch4_kg_per_animal") is not None:
        enteric = {k: float(v) for k, v in raw_enteric.items()}
    else:
        enteric = align_enteric_factors_to_scope(
            raw_enteric,
            temporal_scope=scope,
            auto_prorate=auto_prorate,
        )

    raw_energy = params.get("energy_co2_kg_per_unit") or default_energy_co2_kg_per_unit_yearly_basis()
    energy_keys = farm_input.energy_consumption_by_vector
    raw_energy_filtered = {k: v for k, v in raw_energy.items() if k in energy_keys}
    if params.get("energy_co2_kg_per_unit") is not None:
        energy = {k: float(v) for k, v in raw_energy_filtered.items()}
    else:
        energy = align_energy_factors_to_scope(
            raw_energy_filtered,
            temporal_scope=scope,
            auto_prorate=auto_prorate,
        )

    gwp = params.get("gwp")
    if gwp is None and di.gwp_ipcc_ar4:
        gwp = di.gwp_ipcc_ar4()
    else:
        gwp = gwp or config.DEFAULT_GWP

    return {
        "enteric_ch4_kg_per_animal": enteric,
        "manure_kg_per_kg_bw_per_day": dict(
            params.get("manure_kg_per_kg_bw_per_day") or default_manure_kg_per_kg_bw_per_day()
        ),
        "manure_ch4_kg_per_kg_manure": dict(
            params.get("manure_ch4_kg_per_kg_manure") or default_manure_ch4_kg_per_kg_manure()
        ),
        "energy_co2_kg_per_unit": energy,
        "fertilizer_factors": dict(
            params.get("fertilizer_factors") or default_fertilizer_factors()
        ),
        "gwp": dict(gwp),
        "auto_prorate_factors": auto_prorate,
    }


def _build_subcalculations(
    bundle: Any,
    flat: dict[str, float],
    inputs: dict[str, Any],
    factors: dict[str, Any],
    gwp: dict[str, float],
) -> list[dict[str, Any]]:
    """Monta lista auditável de subcálculos com fórmula, gás e CO2e."""
    ch4_enteric = flat.get("ch4_enteric_kg", 0)
    ch4_manure = flat.get("ch4_manure_kg", 0)
    n2o_fert = flat.get("n2o_fertilizer_kg", 0)
    co2_energy = flat.get("co2_energy_kg", 0)
    gwp_ch4 = float(gwp.get("CH4", 25))
    gwp_n2o = float(gwp.get("N2O", 298))

    subs: list[dict[str, Any]] = [
        {
            "id": "enteric",
            "label": "Fermentação entérica",
            "formula": _FORMULAS["enteric"],
            "gas": "CH4",
            "result_kg": ch4_enteric,
            "unit": "kg CH4",
            "co2e_kg": ch4_enteric * gwp_ch4,
            "inputs": {"headcounts_by_category": inputs.get("headcounts_by_category")},
            "factors": {"enteric_ch4_kg_per_animal": factors.get("enteric_ch4_kg_per_animal")},
        },
        {
            "id": "manure",
            "label": "Manejo de dejetos",
            "formula": _FORMULAS["manure"],
            "gas": "CH4",
            "result_kg": ch4_manure,
            "unit": "kg CH4",
            "co2e_kg": ch4_manure * gwp_ch4,
            "inputs": {
                "headcounts_by_category": inputs.get("headcounts_by_category"),
                "body_weight_kg_by_category": inputs.get("body_weight_kg_by_category"),
                "days_in_period": inputs.get("days_in_period"),
            },
            "factors": {
                "manure_kg_per_kg_bw_per_day": factors.get("manure_kg_per_kg_bw_per_day"),
                "manure_ch4_kg_per_kg_manure": factors.get("manure_ch4_kg_per_kg_manure"),
            },
        },
        {
            "id": "fertilizer",
            "label": "Fertilizantes N",
            "formula": _FORMULAS["fertilizer"],
            "gas": "N2O",
            "result_kg": n2o_fert,
            "unit": "kg N2O",
            "co2e_kg": n2o_fert * gwp_n2o,
            "inputs": {"nitrogen_applied_kg": inputs.get("nitrogen_applied_kg")},
            "factors": {"fertilizer_factors": factors.get("fertilizer_factors")},
        },
        {
            "id": "energy",
            "label": "Energia",
            "formula": _FORMULAS["energy"],
            "gas": "CO2",
            "result_kg": co2_energy,
            "unit": "kg CO2",
            "co2e_kg": co2_energy,
            "inputs": {"energy_consumption_by_vector": inputs.get("energy_consumption_by_vector")},
            "factors": {"energy_co2_kg_per_unit": factors.get("energy_co2_kg_per_unit")},
        },
        {
            "id": "total",
            "label": "Total GEE",
            "formula": _FORMULAS["total"],
            "gas": "CO2e",
            "result_kg": flat.get("co2e_total_kg", 0),
            "unit": "kg CO2e",
            "co2e_kg": flat.get("co2e_total_kg", 0),
            "inputs": {},
            "factors": {"gwp": factors.get("gwp")},
        },
    ]

    if flat.get("co2e_intensity_per_milk_liter"):
        subs.append({
            "id": "intensity_liter",
            "label": "Intensidade por litro",
            "formula": _FORMULAS["intensity_liter"],
            "gas": "CO2e",
            "result_kg": flat["co2e_intensity_per_milk_liter"],
            "unit": "kg CO2e/L",
            "co2e_kg": None,
            "inputs": {"milk_liters": inputs.get("milk_liters"), "co2e_total_kg": flat.get("co2e_total_kg")},
            "factors": {},
        })

    if flat.get("co2e_intensity_per_milk_fpcm"):
        subs.append({
            "id": "intensity_fpcm",
            "label": "Intensidade FPCM",
            "formula": _FORMULAS["intensity_fpcm"],
            "gas": "CO2e",
            "result_kg": flat["co2e_intensity_per_milk_fpcm"],
            "unit": "kg CO2e/kg FPCM",
            "co2e_kg": None,
            "inputs": {"milk_kg_fpcm": inputs.get("milk_kg_fpcm"), "co2e_total_kg": flat.get("co2e_total_kg")},
            "factors": {},
        })

    return subs


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
        farm_input, inputs, data_source, input_resolution = _build_farm_input(canonical_dataset, params)
        factors = _resolve_factors(params, farm_input)

        scope_label = (
            farm_input.temporal_scope.value.upper()
            if hasattr(farm_input.temporal_scope, "value")
            else str(params.get("temporal_scope", "MONTHLY"))
        )
        inputs["days_in_period"] = farm_input.days_in_period
        inputs["temporal_scope"] = scope_label

        bundle = di.compute_farm_period_emissions(
            farm_input,
            enteric_ch4_kg_per_animal=factors["enteric_ch4_kg_per_animal"],
            manure_kg_per_kg_bw_per_day=factors["manure_kg_per_kg_bw_per_day"],
            manure_ch4_kg_per_kg_manure=factors["manure_ch4_kg_per_kg_manure"],
            energy_co2_kg_per_unit=factors["energy_co2_kg_per_unit"],
            fertilizer_factors=factors["fertilizer_factors"],
            gwp=factors["gwp"],
            auto_prorate_factors=factors["auto_prorate_factors"],
            include_provenance=True,
        )
        flat = bundle.to_flat_dict()
        gwp = factors["gwp"]

        by_source = {
            "Fermentação entérica — CH₄": flat.get("ch4_enteric_kg", 0) * gwp["CH4"],
            "Manejo de dejetos — CH₄": flat.get("ch4_manure_kg", 0) * gwp["CH4"],
            "Fertilizantes — N₂O": flat.get("n2o_fertilizer_kg", 0) * gwp["N2O"],
            "Energia — CO₂": flat.get("co2_energy_kg", 0),
        }

        prov = bundle.provenance
        method = {
            "code": prov.method_code if prov else "ECOFARM-T1-DAIRY",
            "version": prov.method_version if prov else "1.0.0",
            "implementation_version": prov.implementation_version if prov else "0.3.0",
            "methodology_label": params.get("methodology", "IPCC/IDF-compatible"),
        }

        temporal = {
            "scope": scope_label,
            "days_in_period": farm_input.days_in_period,
            "auto_prorate_factors": factors["auto_prorate_factors"],
        }

        factors_used = {
            "enteric_ch4_kg_per_animal": factors["enteric_ch4_kg_per_animal"],
            "manure_kg_per_kg_bw_per_day": factors["manure_kg_per_kg_bw_per_day"],
            "manure_ch4_kg_per_kg_manure": factors["manure_ch4_kg_per_kg_manure"],
            "energy_co2_kg_per_unit": factors["energy_co2_kg_per_unit"],
            "fertilizer_factors": factors["fertilizer_factors"],
            "gwp": factors["gwp"],
        }

        subcalculations = _build_subcalculations(bundle, flat, inputs, factors_used, gwp)

        result = {
            "source": "real",
            "mode": "real",
            "data_source": data_source,
            "method": method,
            "temporal": temporal,
            "inputs": inputs,
            "input_resolution": input_resolution,
            "factors_used": factors_used,
            "subcalculations": subcalculations,
            "ch4_enteric_kg": flat.get("ch4_enteric_kg", 0),
            "ch4_manure_kg": flat.get("ch4_manure_kg", 0),
            "n2o_fertilizer_kg": flat.get("n2o_fertilizer_kg", 0),
            "co2_energy_kg": flat.get("co2_energy_kg", 0),
            "co2e_total_kg": flat.get("co2e_total_kg", 0),
            "co2e_intensity_per_milk_liter": flat.get("co2e_intensity_per_milk_liter", 0),
            "co2e_per_animal": flat.get("co2e_total_kg", 0) / max(sum(farm_input.headcounts_by_category.values()), 1),
            "methodology": method["methodology_label"],
            "calculation_version": method["implementation_version"],
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
        hash_payload = {
            "method": result["method"],
            "temporal": result["temporal"],
            "inputs": result["inputs"],
            "factors_used": result["factors_used"],
            "subcalculations": result["subcalculations"],
            "co2e_total_kg": result["co2e_total_kg"],
        }
        result["preliminary_hash"] = sha256_dict(hash_payload)
        return result
    except Exception as exc:
        logger.warning("Cálculo real falhou: %s", exc)
        if not config.ALLOW_MOCK_FALLBACK:
            raise
        return _mock(canonical_dataset, params, reason=str(exc))
