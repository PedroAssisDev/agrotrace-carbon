"""Testes RF005/RNF006 — Lot e hierarquia organizacional."""

from __future__ import annotations

from pathlib import Path

import pytest

from ontology.builder import build_full_ontology
from ontology.cycle_model import (
    OrganizationalConsistencyError,
    normalize_granularity,
    normalize_organizational_granularity,
    upsert_animal,
    upsert_emission_cycle,
    upsert_lot,
    upsert_observation,
    upsert_property,
)
from ontology.exporters import export_ontology
from ontology.population import populate_from_dataframe
from ontology.query_service import (
    list_animals_for_lot,
    list_lots_for_property,
    resolve_organizational_chain,
)
from ontology.validators import validate_organizational_consistency, validate_schema


def test_schema_includes_lot(base_ontology):
    assert hasattr(base_ontology, "Lot")
    assert hasattr(base_ontology, "belongsToProperty")
    assert hasattr(base_ontology, "belongsToLot")
    assert hasattr(base_ontology, "refersToLot")
    assert validate_schema(base_ontology) == []


def test_create_property_lot_animal_chain(fresh_ontology):
    onto = fresh_ontology
    prop = upsert_property(onto, property_id="FARM-LOT-001", name="Fazenda Lot")
    lot = upsert_lot(onto, lot_id="LOT-01", property_id="FARM-LOT-001")
    animal = upsert_animal(
        onto,
        animal_id="ANIMAL-01",
        property_id="FARM-LOT-001",
        lot_id="LOT-01",
    )
    assert list(lot.belongsToProperty)[0] == prop
    assert list(animal.belongsToLot)[0] == lot
    assert list(animal.belongsToProperty)[0] == prop
    chain = resolve_organizational_chain(onto, animal_id="ANIMAL-01")
    assert chain == {
        "animal_id": "ANIMAL-01",
        "lot_id": "LOT-01",
        "property_id": "FARM-LOT-001",
    }
    assert list_lots_for_property(onto, "FARM-LOT-001")[0]["lot_id"] == "LOT-01"
    assert list_animals_for_lot(onto, "LOT-01")[0]["animal_id"] == "ANIMAL-01"


def test_observation_refers_to_lot(fresh_ontology):
    onto = fresh_ontology
    upsert_emission_cycle(
        onto,
        cycle_id="CYCLE-LOT-OBS",
        property_id="FARM-LOT-001",
        reporting_period="2026-01",
        organizational_granularity="lot",
        lot_id="LOT-01",
    )
    row = upsert_observation(
        onto,
        cycle_id="CYCLE-LOT-OBS",
        property_id="FARM-LOT-001",
        variable="herd_count",
        value=42.0,
        unit="animals",
        lot_id="LOT-01",
        organizational_granularity="lot",
    )
    assert row["lot_id"] == "LOT-01"
    obs = onto.search_one(iri=f"*#{row['observation_key']}")
    assert obs is not None
    assert list(obs.refersToLot)
    assert list(obs.refersToLot)[0].hasIdentifier[0] == "LOT-01"


def test_invalid_cross_property_association(fresh_ontology):
    onto = fresh_ontology
    upsert_lot(onto, lot_id="LOT-A", property_id="FARM-A")
    with pytest.raises(OrganizationalConsistencyError):
        upsert_animal(
            onto,
            animal_id="ANIMAL-X",
            property_id="FARM-B",
            lot_id="LOT-A",
        )


def test_lot_id_required_only_when_granularity_lot(fresh_ontology):
    onto = fresh_ontology
    # property granularity — lot_id optional
    upsert_emission_cycle(
        onto,
        cycle_id="CYCLE-PROP",
        property_id="FARM-P",
        reporting_period="2026-01",
        organizational_granularity="property",
    )
    upsert_observation(
        onto,
        cycle_id="CYCLE-PROP",
        property_id="FARM-P",
        variable="milk",
        value=10.0,
        organizational_granularity="property",
    )
    with pytest.raises(ValueError, match="lot_id é obrigatório"):
        upsert_emission_cycle(
            onto,
            cycle_id="CYCLE-NEED-LOT",
            property_id="FARM-P",
            reporting_period="2026-02",
            organizational_granularity="lot",
        )


def test_legacy_cycle_without_lot_id_readable(fresh_ontology):
    """Artefatos antigos sem lot_id continuam legíveis."""
    onto = fresh_ontology
    cycle = upsert_emission_cycle(
        onto,
        cycle_id="CYCLE-LEGACY",
        property_id="FARM-LEGACY",
        reporting_period="2025-12",
        organizational_granularity="property",
    )
    assert not list(getattr(cycle, "refersToLot", None) or [])
    upsert_observation(
        onto,
        cycle_id="CYCLE-LEGACY",
        property_id="FARM-LEGACY",
        variable="energy",
        value=1.0,
    )
    issues = validate_organizational_consistency(onto)
    assert issues == []


def test_serialize_deserialize_lot_relations(tmp_path: Path, fresh_ontology):
    onto = fresh_ontology
    upsert_animal(
        onto,
        animal_id="ANIMAL-S",
        property_id="FARM-S",
        lot_id="LOT-S",
    )
    out = tmp_path / "lot_roundtrip.owl"
    export_ontology(onto, str(out), format="rdfxml")
    from owlready2 import get_ontology

    with open(out, "rb") as fh:
        reloaded = get_ontology("http://example.org/agromrv-lite-reload#").load(fileobj=fh)
    chain = resolve_organizational_chain(reloaded, animal_id="ANIMAL-S")
    assert chain is not None
    assert chain["lot_id"] == "LOT-S"
    assert chain["property_id"] == "FARM-S"


def test_temporal_aliases_preserved():
    assert normalize_granularity("year") == "annual"
    assert normalize_granularity("daily") == "daily"
    assert normalize_granularity("monthly") == "monthly"
    assert normalize_organizational_granularity("lote") == "lot"
    assert normalize_organizational_granularity("ANIMAL") == "animal"


def test_populate_dataframe_with_lot_id(fresh_ontology):
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "property_id": "FARM-POP",
                "lot_id": "LOT-POP",
                "animal_id": "A1",
                "date": "2026-01-15",
                "milk": "20.5",
                "weight": "450",
                "_organizational_context": {"granularity": "animal", "identifier": "A1"},
                "_temporal_context": {
                    "type": "instant",
                    "date": "2026-01-15",
                    "granularity": "day",
                },
            }
        ]
    )
    populate_from_dataframe(onto=fresh_ontology, df=df, layout_name="daily_production")
    chain = resolve_organizational_chain(fresh_ontology, animal_id="A1")
    assert chain == {
        "animal_id": "A1",
        "lot_id": "LOT-POP",
        "property_id": "FARM-POP",
    }
