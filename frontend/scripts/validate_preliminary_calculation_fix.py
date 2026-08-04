"""Validação numérica do cálculo preliminar (correções do diagnóstico).

Cobre o payload Embrapa P-9 2021-11 e asserts de aceite:
- milk = milk_production (sem somar sales)
- N/energia ausentes → 0 (não seeds)
- fatores de energia sem /12
- dias do período pelo calendário / intervalo temporal
- pesos default por categoria
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "agrotrace-carbon-calculation-service"))

from services import calculation_adapter  # noqa: E402


EMBRAPA_P9_2021_11 = {
    "property_id": "P-9",
    "milk_production": 4039.0,
    "milk_sales": 4039.0,
    "number_of_lactating_cows": 13.0,
    "reproducers": 2.0,
    "lactating_cows": 13.0,
    "dry_cows": 3.0,
    "pregnant_heifers": 0.0,
    "heifers_in_raising": 9.0,
    "suckling_calves_female": 1.0,
    "suckling_calves_male": 0.0,
    "male_calves_in_raising": 0.0,
    "male_calves_in_fattening": 0.0,
    "draft_and_breeding_bulls": 0.0,
    "number_of_dry_cows": 13.0,
    "period_start": "2021-11-01",
    "period_end": "2021-11-30",
    "_temporal_context": {
        "type": "interval",
        "start": "2021-11-01",
        "end": "2021-11-30",
        "granularity": "month",
    },
}


def _check(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  OK:   {msg}")


def main() -> int:
    errors: list[str] = []
    print("=== validate_preliminary_calculation_fix ===")

    payload = {
        "reporting_period": "2021-11",
        "frequency": "monthly",
        "normalized_data": [EMBRAPA_P9_2021_11],
        "normalized_payload": [EMBRAPA_P9_2021_11],
        "factor_catalog": None,
    }
    params = {"gwp": {"CH4": 25.0, "N2O": 298.0}, "temporal_scope": "monthly"}

    result = calculation_adapter.run_emission_calculation(payload, params)
    inputs = result.get("inputs") or {}
    factors = result.get("factors_used") or {}
    resolution = {r["slot"]: r for r in (result.get("input_resolution") or [])}

    _check(result.get("mode") == "real", "cálculo em modo real", errors)
    _check(inputs.get("milk_liters") == 4039.0, f"leite=4039 (obtido {inputs.get('milk_liters')})", errors)
    _check(inputs.get("nitrogen_applied_kg") == 0.0, f"N=0 (obtido {inputs.get('nitrogen_applied_kg')})", errors)

    energy = inputs.get("energy_consumption_by_vector") or {}
    _check(energy.get("Diesel", -1) == 0.0, f"Diesel=0 (obtido {energy.get('Diesel')})", errors)
    _check(
        energy.get("Electricity_Grid", -1) == 0.0,
        f"Electricity=0 (obtido {energy.get('Electricity_Grid')})",
        errors,
    )

    diesel_ef = (factors.get("energy_co2_kg_per_unit") or {}).get("Diesel")
    _check(diesel_ef == 2.68, f"EF Diesel=2.68 sem /12 (obtido {diesel_ef})", errors)

    days = (result.get("temporal") or {}).get("days_in_period")
    _check(days == 30, f"dias=30 para nov/2021 (obtido {days})", errors)

    bw = inputs.get("body_weight_kg_by_category") or {}
    _check(bw.get("Calves") == 120.0, f"peso bezerro default=120 (obtido {bw.get('Calves')})", errors)
    _check(
        bw.get("Lactating_Cows") == 550.0,
        f"peso lactante default=550 (obtido {bw.get('Lactating_Cows')})",
        errors,
    )

    n_res = resolution.get("nitrogen_applied_kg") or {}
    _check(n_res.get("status") == "MISSING_ZERO", "resolution N=MISSING_ZERO", errors)
    _check(n_res.get("value") == 0.0, "resolution N value=0", errors)
    _check(
        n_res.get("value") == inputs.get("nitrogen_applied_kg"),
        "resolution N == inputs N",
        errors,
    )

    # Enteric: 13*100/12 + 3*50/12 + 9*30/12 + 1*20/12 + 2*10/12
    expected_enteric = (
        13 * (100 / 12)
        + 3 * (50 / 12)
        + 9 * (30 / 12)
        + 1 * (20 / 12)
        + 2 * (10 / 12)
    )
    ch4_e = float(result.get("ch4_enteric_kg") or 0)
    _check(
        abs(ch4_e - expected_enteric) < 1e-6,
        f"enteric CH4 ~ {expected_enteric:.6f} (obtido {ch4_e})",
        errors,
    )

    # Sem N e sem energia, CO2 energia e N2O devem ser 0
    _check(float(result.get("n2o_fertilizer_kg") or 0) == 0.0, "N2O fertilizante=0", errors)
    _check(float(result.get("co2_energy_kg") or 0) == 0.0, "CO2 energia=0", errors)

    # Fevereiro: 28 dias
    feb_row = {
        **EMBRAPA_P9_2021_11,
        "period_start": "2021-02-01",
        "period_end": "2021-02-28",
        "_temporal_context": {
            "type": "interval",
            "start": "2021-02-01",
            "end": "2021-02-28",
            "granularity": "month",
        },
    }
    feb = calculation_adapter.run_emission_calculation(
        {
            "reporting_period": "2021-02",
            "frequency": "monthly",
            "normalized_data": [feb_row],
        },
        params,
    )
    _check(
        (feb.get("temporal") or {}).get("days_in_period") == 28,
        f"fev/2021 dias=28 (obtido {(feb.get('temporal') or {}).get('days_in_period')})",
        errors,
    )

    # Catálogo ontológico: Diesel permanece 2.68
    from services.calculation_factor_catalog import build_default_factor_catalog

    catalog = build_default_factor_catalog(source="ontology")
    with_cat = calculation_adapter.run_emission_calculation(
        {
            "reporting_period": "2021-11",
            "frequency": "monthly",
            "normalized_data": [EMBRAPA_P9_2021_11],
            "factor_catalog": catalog,
        },
        {"temporal_scope": "monthly"},  # GWP vem do catálogo
    )
    sources = with_cat.get("factor_sources") or {}
    _check(
        sources.get("enteric_ch4_kg_per_animal") == "ontology",
        f"fonte enteric=ontology (obtido {sources.get('enteric_ch4_kg_per_animal')})",
        errors,
    )
    _check(
        (with_cat.get("factors_used") or {}).get("energy_co2_kg_per_unit", {}).get("Diesel") == 2.68,
        "catálogo ontológico: Diesel EF=2.68",
        errors,
    )

    print()
    if errors:
        print(f"RESULTADO: {len(errors)} falha(s)")
        return 1
    print("RESULTADO: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
