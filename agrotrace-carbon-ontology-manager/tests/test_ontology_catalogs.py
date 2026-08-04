"""Tests for canonical variables and units catalogs."""

from ontology.catalogs import get_catalog_individual


def test_canonical_variables_created(fresh_ontology):
    onto = fresh_ontology
    required = [
        "barley", "maize_silage", "lactating_cows", "lactating_cows_weight",
        "diesel", "electricity_grid", "total_milk_production", "ef_enteric_kg_ch4",
        "enteric_tco2e", "dry_matter_intake", "energy_density",
    ]
    for name in required:
        assert get_catalog_individual(onto, "variables", name) is not None


def test_units_created(fresh_ontology):
    onto = fresh_ontology
    required = [
        "kg", "liter", "head", "kg_ch4", "kg_n2o", "kg_co2", "kg_co2e",
        "tonne_co2e", "kg_dm_per_day", "mj_per_kg_dm",
    ]
    for name in required:
        assert get_catalog_individual(onto, "units", name) is not None
