"""Validação numérica do cálculo preliminar via fluxo oficial.

Cobre o payload Embrapa P-9 2021-11 e asserts de aceite:
- criação do ciclo → preparação semântica → materialização do catálogo → cálculo
- milk = milk_production (sem somar sales)
- N/energia ausentes → 0 (não seeds)
- fatores de energia sem /12
- dias do período pelo calendário / intervalo temporal
- pesos default por categoria
- factor_catalog completo com pending, unidades e versão
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "agrotrace-carbon-calculation-service"))
sys.path.insert(0, str(REPO / "agrotrace-carbon-ontology-manager"))

from scripts._validation_env import isolated_data_root  # noqa: E402
from services import calculation_adapter  # noqa: E402
from services import local_orchestrator  # noqa: E402
from services import ontology_runtime_cache as onto_cache  # noqa: E402
from services.calculation_factor_catalog import FACTOR_GROUPS  # noqa: E402
from services.factor_catalog_materialization_service import (  # noqa: E402
    catalog_is_complete,
    missing_required_groups,
)
from services.ontology_adapter import publish_to_canonical_model  # noqa: E402


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


def _build_prepared_cycle(cycle_id: str, row: dict, period: str) -> dict:
    onto_cache.clear()
    cycle: dict = {
        "cycle_id": cycle_id,
        "property_id": "P-9",
        "property_name": "Embrapa P-9",
        "reporting_period": period,
        "frequency": "monthly",
        "granularity": "monthly",
        "normalized_data": [row],
        "wrapper": {"layout_id": "monthly:v1", "normalized_payload": [row]},
        "steps": {
            "ontology": {"status": "DONE"},
            "semantic": {"status": "DONE"},
        },
        "semantic_validation": {
            "critical_errors": 0,
            "warnings": 0,
            "status": "SEMANTIC_VALIDATION_APPROVED",
        },
        "errors": [],
    }
    ontology_result = publish_to_canonical_model({
        "normalized_payload": [row],
        "layout_id": "monthly:v1",
        "cycle_id": cycle_id,
    })
    cycle["ontology"] = {k: v for k, v in ontology_result.items() if k != "_ontology"}
    if ontology_result.get("_ontology") is not None:
        onto_cache.set_ontology(cycle_id, ontology_result["_ontology"])
    if ontology_result.get("parameter_events"):
        cycle["ontology_parameter_events"] = list(ontology_result["parameter_events"])
    return cycle


def _run_checks() -> list[str]:
    errors: list[str] = []
    print("=== validate_preliminary_calculation_form ===")

    # ── Fluxo oficial: ciclo → ontologia → catálogo → cálculo ───────────────
    print("\n[1] preparação semântica + materialização do catálogo")
    onto_cache.clear()
    cycle = _build_prepared_cycle("VAL-PRELIM-P9-2021-11", EMBRAPA_P9_2021_11, "2021-11")
    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    _check(catalog_is_complete(catalog), "factor_catalog completo após publish", errors)
    _check(not missing_required_groups(catalog), "sem grupos obrigatórios ausentes", errors)
    for group in FACTOR_GROUPS:
        _check(group in catalog and isinstance(catalog[group], dict), f"grupo {group} presente", errors)
    statuses = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    _check(
        statuses.get("Lactating_Cows") == "pending",
        f"Lactating_Cows pending (obtido {statuses.get('Lactating_Cows')})",
        errors,
    )
    _check(bool(catalog.get("_version")), f"versão presente ({catalog.get('_version')})", errors)
    _check(bool(catalog.get("_units")), "unidades presentes no catálogo", errors)
    _check(
        (catalog.get("enteric_ch4_kg_per_animal") or {}).get("Lactating_Cows") == 100.0,
        "default anual Lactating_Cows=100",
        errors,
    )

    print("\n[2] cálculo preliminar via orquestrador")
    cycle = local_orchestrator.run_calculation_step(cycle, {"temporal_scope": "monthly"})
    result = cycle.get("calculation") or {}
    _check(result.get("mode") == "real" or bool(result.get("co2e_total_kg")), "cálculo em modo real", errors)
    _check(bool(result), f"cálculo presente (erro={cycle.get('errors')})", errors)

    inputs = result.get("inputs") or {}
    factors = result.get("factors_used") or {}
    resolution = {r["slot"]: r for r in (result.get("input_resolution") or [])}

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

    _check(float(result.get("n2o_fertilizer_kg") or 0) == 0.0, "N2O fertilizante=0", errors)
    _check(float(result.get("co2_energy_kg") or 0) == 0.0, "CO2 energia=0", errors)

    # ── Fevereiro: 28 dias ──────────────────────────────────────────────────
    print("\n[3] fevereiro (28 dias)")
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
    feb_cycle = _build_prepared_cycle("VAL-PRELIM-P9-2021-02", feb_row, "2021-02")
    feb_cycle = local_orchestrator.run_calculation_step(feb_cycle, {"temporal_scope": "monthly"})
    feb = feb_cycle.get("calculation") or {}
    _check(
        (feb.get("temporal") or {}).get("days_in_period") == 28,
        f"dias=28 para fev/2021 (obtido {(feb.get('temporal') or {}).get('days_in_period')})",
        errors,
    )

    # ── Explicabilidade ─────────────────────────────────────────────────────
    print("\n[4] calc_explanation_v1")
    expl = result.get("explanation") or {}
    _check(
        str(expl.get("schema_version") or "").startswith("calc_explanation"),
        f"schema_version explanation ({expl.get('schema_version')})",
        errors,
    )
    sources = expl.get("sources") or []
    factor_origins = set()
    for src in sources:
        for fac in src.get("factors") or []:
            if fac.get("origin"):
                factor_origins.add(fac["origin"])
            if fac.get("unit"):
                break
    _check(bool(sources), "explanation.sources presente", errors)
    _check(
        factor_origins & {"default", "inferred", "configured"},
        f"origins de fator presentes ({factor_origins})",
        errors,
    )
    events = cycle.get("ontology_parameter_events") or []
    _check(
        any(e.get("event") == "catalog_materialized" for e in events)
        or catalog_is_complete((cycle.get("ontology") or {}).get("factor_catalog")),
        "trilha de materialização do catálogo",
        errors,
    )

    # ── Guard: adapter sem catálogo continua bloqueando ─────────────────────
    print("\n[5] guard do adapter (sem catálogo)")
    raised = False
    try:
        calculation_adapter.run_emission_calculation(
            {
                "reporting_period": "2021-11",
                "frequency": "monthly",
                "normalized_data": [EMBRAPA_P9_2021_11],
                "factor_catalog": None,
            },
            {"temporal_scope": "monthly"},
        )
    except RuntimeError as exc:
        raised = "factor_catalog" in str(exc) or "ausentes" in str(exc)
        _check(raised, f"RuntimeError por catálogo ausente ({exc})", errors)
    if not raised:
        _check(False, "esperava RuntimeError sem factor_catalog", errors)

    print(f"\n=== Resultado: {len(errors)} falha(s) ===")
    for e in errors:
        print(f"  - {e}")
    return errors


def main() -> int:
    with isolated_data_root():
        errors = _run_checks()
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
