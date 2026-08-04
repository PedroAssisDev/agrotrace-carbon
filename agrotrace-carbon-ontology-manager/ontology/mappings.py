"""Variable-to-observation and variable-to-unit mappings."""

from __future__ import annotations

from typing import Callable

# Columns that populate context/records, not observations
CONTEXT_COLUMNS = frozenset({
    "_organizational_context",
    "_temporal_context",
    "property_name",
    "property_id",
    "owner_name",
    "information_responsible",
    "location",
    "year",
    "date",
    "period_start",
    "period_end",
    "animal_id",
})

# Ambiguous `total` resolved by layout
TOTAL_LAYOUT_ALIASES: dict[str, str] = {
    "emissions": "total_ghg_co2e",
    "feed": "total_feed_input",
    "default": "total",
}

VARIABLE_CLASS_MAP: dict[str, str] = {}

FEED_VARS = [
    "barley", "beans_peas", "brewers_grain_brewery_residue", "cassava_tapioca",
    "citrus_pulp", "cottonseed_cake_meal", "crop_residues", "ddg", "grass_fresh",
    "grass_hay_off_farm", "grass_hay_on_farm", "grass_silage_on_or_off_farm",
    "hay_oat_clover", "lucerne_alfalfa_hay", "lucerne_alfalfa_silage", "maize_grain",
    "maize_silage", "mineral_mix", "oats", "other_cereals", "other_feed",
    "other_fodder", "rapeseed_cake_meal", "rice", "rye", "sorghum", "sorghum_silage",
    "soybean_meal_hull", "straw_peanut_hull_others", "sugarbeet_molasses",
    "sunflower_cake_meal", "wheat", "milk_powder_dry_matter", "whey_powder",
    "total_feed_input",
]
HERD_VARS = [
    "bulls", "calves", "dry_cows", "females", "males", "heifers", "lactating_cows",
    "draft_and_breeding_bulls", "heifers_in_raising", "male_calves_in_fattening",
    "male_calves_in_raising", "number_of_dry_cows", "number_of_lactating_cows",
    "pregnant_heifers", "reproducers", "suckling_calves_female", "suckling_calves_male",
    "equines_and_mules", "cows_discarded_per_year",
]
WEIGHT_VARS = [
    "bulls_weight", "calves_weight", "dry_cows_weight", "heifers_weight",
    "lactating_cows_weight", "weight",
]
MILK_VARS = ["milk", "milk_production", "total_milk_production", "milk_sales", "productivity"]
MILK_COMP_VARS = ["milk_fat_percentage", "milk_protein_percentage"]
ECONOMIC_VARS = ["milk_gross_price"]
ENERGY_VARS = ["electricity_grid", "photovoltaic_energy"]
FUEL_VARS = ["diesel", "gasoline", "other_fuel"]
FERTILIZER_VARS = ["organic_fertilizer", "non_organic_fertilizer"]
LAND_VARS = ["pasture_area", "area_used_for_dairy_activity"]
SOIL_VARS = ["predominant_soil_type"]
NUTRITION_VARS = ["energy_density", "dry_matter_intake", "dmi_check"]
EMISSION_VARS = ["ef_enteric_kg_ch4", "enteric_tco2e", "total_ghg_co2e", "total"]
ADMIN_VARS = [
    "discarded_cows_destination", "owner_name", "information_responsible",
    "property_name", "property_id", "location", "employees_during_the_month", "total",
]

for v in FEED_VARS:
    VARIABLE_CLASS_MAP[v] = "FeedVariable"
for v in HERD_VARS:
    VARIABLE_CLASS_MAP[v] = "HerdVariable"
for v in WEIGHT_VARS:
    VARIABLE_CLASS_MAP[v] = "WeightVariable"
for v in MILK_VARS:
    VARIABLE_CLASS_MAP[v] = "MilkVariable"
for v in MILK_COMP_VARS:
    VARIABLE_CLASS_MAP[v] = "MilkCompositionVariable"
for v in ECONOMIC_VARS:
    VARIABLE_CLASS_MAP[v] = "EconomicVariable"
for v in ENERGY_VARS:
    VARIABLE_CLASS_MAP[v] = "EnergyVariable"
for v in FUEL_VARS:
    VARIABLE_CLASS_MAP[v] = "FuelVariable"
for v in FERTILIZER_VARS:
    VARIABLE_CLASS_MAP[v] = "FertilizerVariable"
for v in LAND_VARS:
    VARIABLE_CLASS_MAP[v] = "LandVariable"
for v in SOIL_VARS:
    VARIABLE_CLASS_MAP[v] = "SoilVariable"
for v in NUTRITION_VARS:
    VARIABLE_CLASS_MAP[v] = "NutritionVariable"
for v in EMISSION_VARS:
    VARIABLE_CLASS_MAP[v] = "EmissionVariable"
for v in ADMIN_VARS:
    if v not in VARIABLE_CLASS_MAP:
        VARIABLE_CLASS_MAP[v] = "AdministrativeVariable"

VARIABLE_TO_OBSERVATION: dict[str, str] = {}

for v in FEED_VARS:
    VARIABLE_TO_OBSERVATION[v] = "FeedInputObservation"
for v in HERD_VARS:
    VARIABLE_TO_OBSERVATION[v] = "HerdCountObservation"
for v in WEIGHT_VARS:
    VARIABLE_TO_OBSERVATION[v] = "AnimalWeightObservation"
for v in ["milk", "milk_production", "total_milk_production", "productivity"]:
    VARIABLE_TO_OBSERVATION[v] = "MilkProductionObservation"
VARIABLE_TO_OBSERVATION["milk_sales"] = "MilkSalesObservation"
for v in MILK_COMP_VARS:
    VARIABLE_TO_OBSERVATION[v] = "MilkCompositionObservation"
for v in ECONOMIC_VARS:
    VARIABLE_TO_OBSERVATION[v] = "EconomicObservation"
for v in ENERGY_VARS:
    VARIABLE_TO_OBSERVATION[v] = "EnergyUseObservation"
for v in FUEL_VARS:
    VARIABLE_TO_OBSERVATION[v] = "FuelUseObservation"
for v in FERTILIZER_VARS:
    VARIABLE_TO_OBSERVATION[v] = "FertilizerUseObservation"
for v in LAND_VARS:
    VARIABLE_TO_OBSERVATION[v] = "LandUseObservation"
for v in SOIL_VARS:
    VARIABLE_TO_OBSERVATION[v] = "SoilTypeObservation"
for v in NUTRITION_VARS:
    VARIABLE_TO_OBSERVATION[v] = "NutritionObservation"
for v in EMISSION_VARS:
    VARIABLE_TO_OBSERVATION[v] = "EmissionObservation"
VARIABLE_TO_OBSERVATION["discarded_cows_destination"] = "DestinationObservation"
for v in ["owner_name", "information_responsible", "property_name", "property_id"]:
    VARIABLE_TO_OBSERVATION[v] = "AdministrativeObservation"
VARIABLE_TO_OBSERVATION["location"] = "AdministrativeObservation"
VARIABLE_TO_OBSERVATION["employees_during_the_month"] = "AdministrativeObservation"
VARIABLE_TO_OBSERVATION["total"] = "EmissionObservation"


def _granularity_unit(base: str, temporal_granularity: str | None) -> str:
    if not temporal_granularity:
        return base
    gran = temporal_granularity.lower()
    if gran == "day":
        return f"{base}_per_day"
    if gran == "month":
        return f"{base}_per_month"
    if gran == "year":
        return f"{base}_per_year"
    return base


UNIT_RULES: dict[str, str | Callable[[str | None], str]] = {
    **{v: "head" for v in HERD_VARS},
    **{v: "kg" for v in WEIGHT_VARS},
    "milk": lambda g: _granularity_unit("liter", g),
    "milk_production": lambda g: _granularity_unit("liter", g),
    "total_milk_production": lambda g: _granularity_unit("liter", g),
    "milk_sales": lambda g: _granularity_unit("liter", g),
    "milk_gross_price": "currency",
    "milk_fat_percentage": "percentage",
    "milk_protein_percentage": "percentage",
    "productivity": "liter_per_day",
    **{v: lambda g: _granularity_unit("kg", g) for v in FEED_VARS if v != "total_feed_input"},
    "total_feed_input": lambda g: _granularity_unit("kg", g),
    **{v: "liter_fuel" for v in FUEL_VARS},
    **{v: "kWh" for v in ENERGY_VARS},
    **{v: "kg" for v in FERTILIZER_VARS},
    **{v: "hectare" for v in LAND_VARS},
    "predominant_soil_type": "text",
    "discarded_cows_destination": "text",
    "energy_density": "mj_per_kg_dm",
    "dry_matter_intake": "kg_dm_per_day",
    "dmi_check": "kg_dm_per_day",
    "ef_enteric_kg_ch4": "kg_ch4_per_head_month",
    "enteric_tco2e": "tonne_co2e",
    "total_ghg_co2e": "tonne_co2e",
    "total": "tonne_co2e",
    "employees_during_the_month": "head",
    "owner_name": "text",
    "information_responsible": "text",
    "property_name": "text",
    "property_id": "text",
    "location": "text",
}


def resolve_canonical_variable(column_name: str, layout_name: str | None = None) -> str:
    """Resolve column name to canonical variable, handling ambiguous `total`."""
    if column_name == "total" and layout_name:
        return TOTAL_LAYOUT_ALIASES.get(layout_name, TOTAL_LAYOUT_ALIASES["default"])
    return column_name


def get_observation_class_for_variable(
    variable_name: str, layout_name: str | None = None
) -> str:
    """Return observation class name for a canonical variable."""
    canonical = resolve_canonical_variable(variable_name, layout_name)
    if canonical in VARIABLE_TO_OBSERVATION:
        return VARIABLE_TO_OBSERVATION[canonical]
    var_class = VARIABLE_CLASS_MAP.get(canonical, "AdministrativeVariable")
    fallback = {
        "FeedVariable": "FeedInputObservation",
        "HerdVariable": "HerdCountObservation",
        "WeightVariable": "AnimalWeightObservation",
        "MilkVariable": "MilkProductionObservation",
        "MilkCompositionVariable": "MilkCompositionObservation",
        "EnergyVariable": "EnergyUseObservation",
        "FuelVariable": "FuelUseObservation",
        "FertilizerVariable": "FertilizerUseObservation",
        "LandVariable": "LandUseObservation",
        "SoilVariable": "SoilTypeObservation",
        "NutritionVariable": "NutritionObservation",
        "EmissionVariable": "EmissionObservation",
        "EconomicVariable": "EconomicObservation",
        "AdministrativeVariable": "AdministrativeObservation",
    }
    return fallback.get(var_class, "AdministrativeObservation")


def get_expected_unit_for_variable(
    variable_name: str, temporal_granularity: str | None = None
) -> str:
    """Return expected unit name for a variable, optionally depending on granularity."""
    canonical = variable_name
    rule = UNIT_RULES.get(canonical)
    if rule is None:
        var_class = VARIABLE_CLASS_MAP.get(canonical)
        if var_class == "HerdVariable":
            return "head"
        if var_class in ("FeedVariable", "WeightVariable"):
            return _granularity_unit("kg", temporal_granularity)
        return "dimensionless"
    if callable(rule):
        return rule(temporal_granularity)
    return rule


def is_context_column(column_name: str) -> bool:
    return column_name in CONTEXT_COLUMNS


def is_qualitative_variable(variable_name: str) -> bool:
    unit = get_expected_unit_for_variable(variable_name)
    return unit == "text"
