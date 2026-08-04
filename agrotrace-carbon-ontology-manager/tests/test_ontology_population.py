"""Tests for ontology population from normalized data."""

from __future__ import annotations

from ontology.examples import ANNUAL_CSV, DAILY_CSV, DAILY_NUTRITION_CSV, MONTHLY_CSV
from ontology.population import populate_from_dataframe, read_dataframe_from_csv_string


def _obs_for_variable(onto, canonical_name: str):
    return [
        o for o in onto.Observation.instances()
        if o.observesVariable
        and o.observesVariable[0].hasCanonicalName
        and o.observesVariable[0].hasCanonicalName[0] == canonical_name
    ]


def test_populate_annual_record(fresh_ontology):
    onto = fresh_ontology
    df = read_dataframe_from_csv_string(ANNUAL_CSV)
    populate_from_dataframe(onto, df, layout_name="annual_inventory")

    assert list(onto.AnnualPropertyInventoryRecord.instances())
    assert list(onto.OrganizationalContext.instances())
    assert list(onto.TemporalContext.instances())

    for var in (
        "calves", "lactating_cows", "maize_silage",
        "total_milk_production", "predominant_soil_type",
    ):
        assert _obs_for_variable(onto, var), f"Missing observation for {var}"


def test_populate_daily_animal_record(fresh_ontology):
    onto = fresh_ontology
    df = read_dataframe_from_csv_string(DAILY_CSV)
    populate_from_dataframe(onto, df, layout_name="daily_production")

    assert list(onto.DailyAnimalProductionRecord.instances())
    assert list(onto.Animal.instances())
    assert _obs_for_variable(onto, "milk")
    assert _obs_for_variable(onto, "weight")

    milk_obs = _obs_for_variable(onto, "milk")[0]
    assert milk_obs.__class__.__name__ == "MilkProductionObservation"
    weight_obs = _obs_for_variable(onto, "weight")[0]
    assert weight_obs.__class__.__name__ == "AnimalWeightObservation"


def test_populate_daily_nutrition_record(fresh_ontology):
    onto = fresh_ontology
    df = read_dataframe_from_csv_string(DAILY_NUTRITION_CSV)
    populate_from_dataframe(onto, df, layout_name="daily_nutrition")

    assert list(onto.DailyAnimalNutritionRecord.instances())
    assert _obs_for_variable(onto, "energy_density")
    assert _obs_for_variable(onto, "dry_matter_intake")


def test_populate_monthly_record(fresh_ontology):
    onto = fresh_ontology
    df = read_dataframe_from_csv_string(MONTHLY_CSV)
    populate_from_dataframe(onto, df, layout_name="monthly_property")

    assert list(onto.MonthlyPropertyRecord.instances())
    assert _obs_for_variable(onto, "milk_production")
    # Zero value must not be ignored
    assert _obs_for_variable(onto, "draft_and_breeding_bulls")
