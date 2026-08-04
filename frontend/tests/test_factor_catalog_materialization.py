"""Materialização do factor_catalog — RF008/RF009 (defaults pending, guard, explanation)."""

from __future__ import annotations

import pytest

from services.calculation_adapter import _resolve_factors, run_emission_calculation
from services.calculation_factor_catalog import FACTOR_GROUPS, build_default_factor_catalog
from services.factor_catalog_materialization_service import (
    catalog_is_complete,
    ensure_factor_catalog_for_calculation,
    factor_units_for_catalog,
    materialize_factor_catalog,
    missing_required_groups,
    status_to_explanation_origin,
)
from services import local_orchestrator
from services import ontology_runtime_cache as onto_cache
from services.ontology_adapter import publish_to_canonical_model


EMBRAPA = {
    "property_id": "P-9",
    "milk_production": 4039.0,
    "milk_sales": 4039.0,
    "lactating_cows": 13.0,
    "dry_cows": 3.0,
    "pregnant_heifers": 0.0,
    "heifers_in_raising": 9.0,
    "suckling_calves_female": 1.0,
    "suckling_calves_male": 0.0,
    "male_calves_in_raising": 0.0,
    "male_calves_in_fattening": 0.0,
    "draft_and_breeding_bulls": 0.0,
    "reproducers": 2.0,
    "period_start": "2021-11-01",
    "period_end": "2021-11-30",
    "_temporal_context": {
        "type": "interval",
        "start": "2021-11-01",
        "end": "2021-11-30",
        "granularity": "month",
    },
}


def _bare_cycle(cycle_id: str = "T-CAT") -> dict:
    return {
        "cycle_id": cycle_id,
        "property_id": "P-9",
        "reporting_period": "2021-11",
        "frequency": "monthly",
        "granularity": "monthly",
        "normalized_data": [EMBRAPA],
        "wrapper": {"layout_id": "monthly:v1"},
        "steps": {
            "ontology": {"status": "DONE"},
            "semantic": {"status": "DONE"},
        },
        "semantic_validation": {"critical_errors": 0, "warnings": 0},
        "errors": [],
        "ontology": {},
    }


def test_catalog_complete_from_defaults() -> None:
    catalog = build_default_factor_catalog(source="ontology")
    assert catalog_is_complete(catalog)
    assert missing_required_groups(catalog) == []
    for g in FACTOR_GROUPS:
        assert g in catalog


def test_parameter_pending_on_materialize() -> None:
    cycle = _bare_cycle("T-PENDING")
    catalog = materialize_factor_catalog(cycle)
    st = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    assert st.get("Lactating_Cows") == "pending"
    assert (catalog.get("enteric_ch4_kg_per_animal") or {}).get("Lactating_Cows") == 100.0
    events = cycle.get("ontology_parameter_events") or []
    assert any(e.get("event") == "catalog_materialized" for e in events)


def test_missing_parameter_blocks_resolve() -> None:
    class FakeFarm:
        temporal_scope = type("S", (), {"value": "monthly"})()
        energy_consumption_by_vector = {"Diesel": 0.0}

    with pytest.raises(RuntimeError, match="factor_catalog"):
        _resolve_factors({}, FakeFarm(), factor_catalog=None)

    with pytest.raises(RuntimeError, match="factor_catalog"):
        _resolve_factors({}, FakeFarm(), factor_catalog={"gwp": {}})


def test_version_and_units() -> None:
    cycle = _bare_cycle("T-UNITS")
    catalog = materialize_factor_catalog(cycle)
    assert catalog.get("_version")
    units = catalog.get("_units") or factor_units_for_catalog()
    assert units.get("enteric_ch4_kg_per_animal")
    assert units.get("gwp")


def test_gwp_absent_raises() -> None:
    class FakeFarm:
        temporal_scope = type("S", (), {"value": "monthly"})()
        energy_consumption_by_vector = {}

    catalog = build_default_factor_catalog()
    catalog["gwp"] = {}
    with pytest.raises(RuntimeError, match="gwp|GWP"):
        _resolve_factors({}, FakeFarm(), factor_catalog=catalog)


def test_status_to_origin_mapping() -> None:
    assert status_to_explanation_origin("pending") == "default"
    assert status_to_explanation_origin("corrected") == "configured"
    assert status_to_explanation_origin("confirmed") == "configured"
    assert status_to_explanation_origin("published") == "configured"


def test_persist_on_cycle_ontology(agrotrace_data_root) -> None:
    cycle = _bare_cycle("T-PERSIST")
    catalog = materialize_factor_catalog(cycle)
    assert (cycle.get("ontology") or {}).get("factor_catalog") is catalog
    assert catalog_is_complete(cycle["ontology"]["factor_catalog"])


def test_does_not_overwrite_corrected() -> None:
    cycle = _bare_cycle("T-PROT")
    cycle["ontology"] = {
        "factor_catalog": {
            "enteric_ch4_kg_per_animal": {"Lactating_Cows": 120.0},
            "_statuses": {"enteric_ch4_kg_per_animal": {"Lactating_Cows": "corrected"}},
        }
    }
    catalog = materialize_factor_catalog(cycle)
    assert catalog["enteric_ch4_kg_per_animal"]["Lactating_Cows"] == 120.0
    assert catalog["_statuses"]["enteric_ch4_kg_per_animal"]["Lactating_Cows"] == "corrected"
    assert catalog_is_complete(catalog)


def test_monthly_and_annual_via_orchestrator(agrotrace_data_root) -> None:
    onto_cache.clear()
    monthly = _bare_cycle("T-MONTHLY")
    onto = publish_to_canonical_model({
        "normalized_payload": [EMBRAPA],
        "layout_id": "monthly:v1",
        "cycle_id": "T-MONTHLY",
    })
    monthly["ontology"] = {k: v for k, v in onto.items() if k != "_ontology"}
    if onto.get("_ontology") is not None:
        onto_cache.set_ontology("T-MONTHLY", onto["_ontology"])

    monthly = local_orchestrator.run_calculation_step(monthly, {"temporal_scope": "monthly"})
    calc_m = monthly.get("calculation") or {}
    enteric_m = (calc_m.get("factors_used") or {}).get("enteric_ch4_kg_per_animal") or {}
    assert enteric_m.get("Lactating_Cows") is not None
    assert abs(float(enteric_m["Lactating_Cows"]) - 100.0 / 12.0) < 1e-9

    onto_cache.clear()
    annual_row = {
        **EMBRAPA,
        "period_start": "2021-01-01",
        "period_end": "2021-12-31",
        "_temporal_context": {
            "type": "interval",
            "start": "2021-01-01",
            "end": "2021-12-31",
            "granularity": "year",
        },
    }
    annual = _bare_cycle("T-ANNUAL")
    annual["reporting_period"] = "2021"
    annual["frequency"] = "annual"
    annual["granularity"] = "annual"
    annual["normalized_data"] = [annual_row]
    onto_a = publish_to_canonical_model({
        "normalized_payload": [annual_row],
        "layout_id": "annual:v1",
        "cycle_id": "T-ANNUAL",
    })
    annual["ontology"] = {k: v for k, v in onto_a.items() if k != "_ontology"}
    if onto_a.get("_ontology") is not None:
        onto_cache.set_ontology("T-ANNUAL", onto_a["_ontology"])

    annual = local_orchestrator.run_calculation_step(annual, {"temporal_scope": "annual"})
    calc_a = annual.get("calculation") or {}
    enteric_a = (calc_a.get("factors_used") or {}).get("enteric_ch4_kg_per_animal") or {}
    assert abs(float(enteric_a.get("Lactating_Cows") or 0) - 100.0) < 1e-9


def test_explanation_has_origin_and_unit(agrotrace_data_root) -> None:
    onto_cache.clear()
    cycle = _bare_cycle("T-EXPL")
    onto = publish_to_canonical_model({
        "normalized_payload": [EMBRAPA],
        "layout_id": "monthly:v1",
        "cycle_id": "T-EXPL",
    })
    cycle["ontology"] = {k: v for k, v in onto.items() if k != "_ontology"}
    if onto.get("_ontology") is not None:
        onto_cache.set_ontology("T-EXPL", onto["_ontology"])

    cycle = local_orchestrator.run_calculation_step(cycle, {"temporal_scope": "monthly"})
    expl = (cycle.get("calculation") or {}).get("explanation") or {}
    assert str(expl.get("schema_version") or "").startswith("calc_explanation")
    factors = []
    for src in expl.get("sources") or []:
        factors.extend(src.get("factors") or [])
    assert factors
    assert any(f.get("origin") in {"default", "inferred", "configured"} for f in factors)
    assert any(f.get("unit") for f in factors)


def test_factor_source_origin_from_catalog(agrotrace_data_root) -> None:
    catalog = ensure_factor_catalog_for_calculation(_bare_cycle("T-SRC"))
    assert catalog.get("_source") in {"ontology", "defaults"}
    assert (catalog.get("_statuses") or {}).get("gwp", {}).get("CH4") == "pending"


def test_direct_adapter_without_catalog_raises() -> None:
    with pytest.raises(RuntimeError, match="factor_catalog|ausentes|GWP"):
        run_emission_calculation(
            {
                "reporting_period": "2021-11",
                "frequency": "monthly",
                "normalized_data": [EMBRAPA],
                "factor_catalog": None,
            },
            {"temporal_scope": "monthly"},
        )
