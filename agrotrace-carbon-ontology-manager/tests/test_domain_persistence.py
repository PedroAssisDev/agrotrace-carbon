"""Testes unitários: cycle model + EmissionResult + query service."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ontology import build_full_ontology, export_ontology  # noqa: E402
from ontology.cycle_model import (  # noqa: E402
    list_cycle_observations,
    set_cycle_status,
    upsert_emission_cycle,
    upsert_observation,
    upsert_property,
)
from ontology.query_service import (  # noqa: E402
    OntologyIntegrityError,
    get_emission_summary,
    get_emission_results,
    list_cycles,
    list_properties,
    resolve_ontology_source,
)
from ontology.result_lifecycle import (  # noqa: E402
    list_active_results,
    set_results_status,
    upsert_emission_result,
)


def test_property_cycle_observation_result_roundtrip(tmp_path: Path) -> None:
    onto = build_full_ontology()
    upsert_property(onto, property_id="FARM-T1", name="Fazenda Teste")
    upsert_emission_cycle(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        reporting_period="2022-01",
        temporal_granularity="monthly",
        status="PendingApproval",
        property_name="Fazenda Teste",
    )
    upsert_observation(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        variable="lactating_cows",
        value=13,
        unit="head",
        status="pending",
    )
    upsert_observation(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        variable="milk_production",
        value=4039.0,
        unit="L",
        status="pending",
    )
    r1 = upsert_emission_result(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        reporting_period="2022-01",
        temporal_granularity="monthly",
        formula_id="enteric_fermentation",
        gas="CH4",
        value=100.0,
        unit="kg CH4",
        co2e_value=2500.0,
        emission_source="enteric",
        status="preliminary",
    )
    r2 = upsert_emission_result(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        reporting_period="2022-01",
        temporal_granularity="monthly",
        formula_id="enteric_fermentation",
        gas="CH4",
        value=120.0,
        unit="kg CH4",
        co2e_value=3000.0,
        emission_source="enteric",
        status="recalculated",
    )
    assert r1["result_key"] == r2["result_key"]
    active = list_active_results(onto, "CYCLE-T1")
    assert len(active) == 1
    assert active[0]["value"] == 120.0
    assert active[0]["status"] == "recalculated"

    upsert_emission_result(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        reporting_period="2022-01",
        temporal_granularity="monthly",
        formula_id="total_ghg",
        gas="CO2e",
        value=5000.0,
        unit="kg CO2e",
        co2e_value=5000.0,
        emission_source="total",
        status="preliminary",
    )
    upsert_emission_result(
        onto,
        cycle_id="CYCLE-T1",
        property_id="FARM-T1",
        reporting_period="2022-01",
        temporal_granularity="monthly",
        formula_id="intensity",
        gas="CO2e",
        value=1.237,
        unit="kg CO2e/L",
        emission_source="intensity",
        status="preliminary",
    )

    set_results_status(onto, "CYCLE-T1", "approved")
    set_cycle_status(onto, "CYCLE-T1", "Approved")

    props = list_properties(onto)
    assert any(p["property_id"] == "FARM-T1" for p in props)
    cycles = list_cycles(onto, property_id="FARM-T1")
    assert len(cycles) == 1
    assert cycles[0]["temporal_granularity"] == "monthly"

    obs = list_cycle_observations(onto, "CYCLE-T1")
    assert len(obs) >= 2

    results = get_emission_results(onto, "CYCLE-T1")
    assert any(r["status"] == "approved" for r in results)

    summary = get_emission_summary(onto, "CYCLE-T1")
    assert summary["source"] == "ontology"
    assert summary["co2e_total_kg"] == 5000.0
    assert summary["milk_liters"] == 4039.0
    assert abs(summary["intensity"] - 1.237) < 1e-9

    owl = tmp_path / "work.owl"
    export_ontology(onto, str(owl), format="rdfxml")
    assert owl.exists()


def test_resolve_published_requires_final() -> None:
    try:
        resolve_ontology_source(
            cycle_status="Published",
            working_path="/tmp/work.owl",
            published_path="/tmp/missing_final.owl",
        )
        raise AssertionError("deveria falhar")
    except OntologyIntegrityError:
        pass


def test_yearly_label_rejected() -> None:
    from ontology.cycle_model import normalize_granularity

    with pytest.raises(ValueError, match="Granularidade inválida"):
        normalize_granularity("yearly")
    with pytest.raises(ValueError, match="Granularidade inválida"):
        normalize_granularity("YEARLY")
    assert normalize_granularity("annual") == "annual"


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        test_property_cycle_observation_result_roundtrip(Path(d))
        test_resolve_published_requires_final()
        test_yearly_label_rejected()
    print("OK ontology domain tests")
