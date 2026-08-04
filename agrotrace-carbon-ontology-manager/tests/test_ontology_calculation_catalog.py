"""Tests for calculation method catalog."""

from ontology.catalogs import CALCULATION_METHODS
from ontology.validators import validate_calculation_methods


def test_calculation_catalog_created(fresh_ontology):
    onto = fresh_ontology
    required_methods = [
        "calculate_enteric_fermentation_ch4",
        "calculate_manure_management_ch4",
        "calculate_fertilizer_n2o",
        "calculate_energy_co2",
        "calculate_total_ghg_co2e",
        "monthly_to_annual_sum",
        "monthly_to_annual_proration",
        "batch_runner",
        "environmental_calcs_adapter",
    ]
    fn_names = {m["function_name"] for m in CALCULATION_METHODS}
    for name in required_methods:
        match = [m for m in CALCULATION_METHODS if m["name"] == name]
        assert match, f"Missing method definition {name}"
        assert match[0]["function_name"] in fn_names or match[0]["function_name"]

    individuals = [
        i for i in onto.individuals() if hasattr(i, "hasFunctionName") and i.hasFunctionName
    ]
    created = {i.hasFunctionName[0] for i in individuals}
    for m in CALCULATION_METHODS:
        assert m["function_name"] in created


def test_total_ghg_requires_gwp(fresh_ontology):
    onto = fresh_ontology
    issues = validate_calculation_methods(onto)
    assert not issues, issues
    total = [
        i for i in onto.individuals()
        if hasattr(i, "hasFunctionName")
        and i.hasFunctionName
        and i.hasFunctionName[0] == "calculate_total_ghg_co2e"
    ]
    assert total
    method = total[0]
    assert method.requiresGWPParameterSet == [True]
    assert method.usesGWPParameterSet
