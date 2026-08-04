"""Matriz declarativa: variável ontológica → KPI → seção → prioridade.

Espelha agrotrace-carbon-ontology-manager/ontology/mappings.py sem importar o pacote.
"""

from __future__ import annotations

from typing import Any, Literal

SectionKey = Literal["productivity", "management", "emissions", "sustainability", "business", "auditability"]
Priority = Literal["P1", "P2", "P3"]

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
    "property_name", "property_id", "location", "employees_during_the_month",
]

VARIABLE_CLASS_MAP: dict[str, str] = {}
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
    VARIABLE_CLASS_MAP[v] = "AdministrativeVariable"


def _entry(
    ontology_var: str,
    kpi_key: str,
    section: SectionKey,
    label: str,
    *,
    unit: str = "dimensionless",
    priority: Priority = "P2",
    screens: list[str] | None = None,
    derive: str | None = None,
    aggregate: str = "latest",
) -> dict[str, Any]:
    return {
        "ontology_var": ontology_var,
        "kpi_key": kpi_key,
        "section": section,
        "label": label,
        "unit": unit,
        "priority": priority,
        "screens": screens or ["/indicators"],
        "derive": derive,
        "aggregate": aggregate,
        "ontology_class": VARIABLE_CLASS_MAP.get(ontology_var, "AdministrativeVariable"),
    }


# --- Entradas P1: variáveis diretas mapeadas para KPI ---
P1_DIRECT_ENTRIES: list[dict[str, Any]] = [
    _entry("milk_fat_percentage", "milk_fat_pct", "productivity", "Gordura do leite (%)", unit="percentage", priority="P1", screens=["/indicators", "/"]),
    _entry("milk_protein_percentage", "milk_protein_pct", "productivity", "Proteína do leite (%)", unit="percentage", priority="P1", screens=["/indicators", "/"]),
    _entry("milk_sales", "milk_sales_liters", "productivity", "Leite comercializado (L)", unit="liter", priority="P1", aggregate="sum"),
    _entry("pasture_area", "pasture_area_ha", "management", "Área de pastagem (ha)", unit="hectare", priority="P1"),
    _entry("area_used_for_dairy_activity", "dairy_area_ha", "management", "Área atividade leiteira (ha)", unit="hectare", priority="P1"),
    _entry("total_feed_input", "total_feed_input_kg", "management", "Insumo alimentar total (kg)", unit="kg", priority="P1", aggregate="sum"),
    _entry("dry_matter_intake", "dry_matter_intake", "management", "MS ingerida (kg/dia)", unit="kg_dm_per_day", priority="P1"),
    _entry("energy_density", "energy_density", "management", "Densidade energética (MJ/kg MS)", unit="mj_per_kg_dm", priority="P1"),
    _entry("organic_fertilizer", "organic_fertilizer_kg", "management", "Fertilizante orgânico (kg)", unit="kg", priority="P1", aggregate="sum"),
    _entry("non_organic_fertilizer", "non_organic_fertilizer_kg", "management", "Fertilizante químico (kg)", unit="kg", priority="P1", aggregate="sum"),
    _entry("electricity_grid", "electricity_grid_kwh", "management", "Energia da rede (kWh)", unit="kWh", priority="P1", aggregate="sum"),
    _entry("photovoltaic_energy", "photovoltaic_energy_kwh", "management", "Energia fotovoltaica (kWh)", unit="kWh", priority="P1", aggregate="sum"),
    _entry("milk_gross_price", "milk_gross_price", "business", "Preço bruto do leite", unit="currency", priority="P1"),
    _entry("employees_during_the_month", "employees_count", "business", "Funcionários no mês", unit="head", priority="P1"),
]

# --- KPIs derivados P1 (sem variável única) ---
P1_DERIVED_ENTRIES: list[dict[str, Any]] = [
    {
        "ontology_var": None,
        "kpi_key": "sales_rate_pct",
        "section": "productivity",
        "label": "Taxa de comercialização (%)",
        "unit": "percentage",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "milk_sales / milk_production",
    },
    {
        "ontology_var": None,
        "kpi_key": "liters_per_hectare",
        "section": "productivity",
        "label": "Produção por hectare (L/ha)",
        "unit": "liter_per_hectare",
        "priority": "P1",
        "screens": ["/indicators", "/farm"],
        "derive": "total_milk / pasture_area",
    },
    {
        "ontology_var": None,
        "kpi_key": "estimated_gross_revenue",
        "section": "business",
        "label": "Receita bruta estimada",
        "unit": "currency",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "milk_gross_price * milk_sales",
    },
    {
        "ontology_var": None,
        "kpi_key": "milk_per_employee",
        "section": "business",
        "label": "Produção por funcionário (L)",
        "unit": "liter",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "total_milk / employees",
    },
    {
        "ontology_var": None,
        "kpi_key": "organic_fertilizer_pct",
        "section": "management",
        "label": "Fertilizante orgânico (%)",
        "unit": "percentage",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "organic / (organic + non_organic)",
    },
    {
        "ontology_var": None,
        "kpi_key": "renewable_energy_pct",
        "section": "management",
        "label": "Energia renovável (%)",
        "unit": "percentage",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "photovoltaic / (grid + photovoltaic)",
    },
    {
        "ontology_var": None,
        "kpi_key": "animals_per_hectare",
        "section": "management",
        "label": "Densidade animal (UA/ha)",
        "unit": "head_per_hectare",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "lactating_cows / pasture_area",
    },
    {
        "ontology_var": None,
        "kpi_key": "feed_efficiency",
        "section": "management",
        "label": "Eficiência alimentar (L/kg ração)",
        "unit": "liter_per_kg",
        "priority": "P1",
        "screens": ["/indicators"],
        "derive": "total_milk / total_feed_input",
    },
    {
        "ontology_var": None,
        "kpi_key": "co2e_per_hectare",
        "section": "sustainability",
        "label": "CO₂e por hectare (kg/ha)",
        "unit": "kg_co2e_per_hectare",
        "priority": "P1",
        "screens": ["/indicators", "/"],
        "derive": "co2e_total / pasture_area",
    },
]

# --- P2/P3: registro completo para documentação ---
P2_ENTRIES: list[dict[str, Any]] = [
    _entry("ef_enteric_kg_ch4", "ef_enteric_kg_ch4", "emissions", "Fator entérico (kg CH₄/cab/mês)", priority="P2"),
    _entry("diesel", "diesel_liters", "management", "Diesel (L)", unit="liter_fuel", priority="P2", aggregate="sum"),
    _entry("gasoline", "gasoline_liters", "management", "Gasolina (L)", unit="liter_fuel", priority="P2", aggregate="sum"),
    _entry("cows_discarded_per_year", "cows_discarded_per_year", "management", "Vacas descartadas/ano", unit="head", priority="P2"),
    _entry("dry_cows", "dry_cows_count", "management", "Vacas secas", unit="head", priority="P2"),
]

P3_ENTRIES: list[dict[str, Any]] = [
    _entry("predominant_soil_type", "predominant_soil_type", "management", "Tipo de solo predominante", unit="text", priority="P3"),
    _entry("discarded_cows_destination", "discarded_cows_destination", "management", "Destino vacas descartadas", unit="text", priority="P3"),
    _entry("information_responsible", "information_responsible", "business", "Responsável pela informação", unit="text", priority="P3"),
    _entry("productivity", "declared_productivity", "productivity", "Produtividade declarada (L/dia)", unit="liter_per_day", priority="P3"),
]

# Feed vars P2 — mix de dieta
for _feed in FEED_VARS:
    if _feed != "total_feed_input":
        P2_ENTRIES.append(_entry(
            _feed, f"feed_{_feed}", "management", _feed.replace("_", " ").title(),
            unit="kg", priority="P2", aggregate="sum", screens=["/indicators"],
        ))

ONTOLOGY_KPI_REGISTRY: list[dict[str, Any]] = (
    P1_DIRECT_ENTRIES + P1_DERIVED_ENTRIES + P2_ENTRIES + P3_ENTRIES
)


def entries_by_section(section: SectionKey) -> list[dict[str, Any]]:
    return [e for e in ONTOLOGY_KPI_REGISTRY if e.get("section") == section]


def entries_by_priority(priority: Priority) -> list[dict[str, Any]]:
    return [e for e in ONTOLOGY_KPI_REGISTRY if e.get("priority") == priority]


def direct_var_names(priority: Priority | None = None) -> list[str]:
    names: list[str] = []
    for e in ONTOLOGY_KPI_REGISTRY:
        if e.get("ontology_var") and (priority is None or e.get("priority") == priority):
            names.append(str(e["ontology_var"]))
    return names


# --- Revisão de cálculos: fórmula → variáveis ontológicas ---

FORMULA_ONTOLOGY_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "enteric_fermentation_ch4": [
        {"ontology_var": "lactating_cows", "expected_unit": "head", "semantic": "headcount"},
        {"ontology_var": "dry_cows", "expected_unit": "head", "semantic": "headcount"},
        {"ontology_var": "heifers", "expected_unit": "head", "semantic": "headcount"},
        {"ontology_var": "calves", "expected_unit": "head", "semantic": "headcount"},
    ],
    "manure_management_ch4": [
        {"ontology_var": "lactating_cows", "expected_unit": "head", "semantic": "headcount"},
        {"ontology_var": "lactating_cows_weight", "expected_unit": "kg", "semantic": "weight"},
    ],
    "fertilizer_n2o": [
        {"ontology_var": "non_organic_fertilizer", "expected_unit": "kg", "semantic": "nitrogen"},
    ],
    "energy_co2": [
        {"ontology_var": "diesel", "expected_unit": "L", "semantic": "energy"},
        {"ontology_var": "electricity_grid", "expected_unit": "kWh", "semantic": "energy"},
    ],
    "total_ghg_co2e": [],
    "intensity_co2e_per_liter": [
        {"ontology_var": "milk_production", "expected_unit": "L", "semantic": "production"},
    ],
}

ONTOLOGY_VAR_ALIASES: dict[str, list[str]] = {
    "milk_production": ["milk", "total_milk_production", "milk_sales"],
    "lactating_cows": ["number_of_lactating_cows"],
    "dry_cows": ["number_of_dry_cows"],
    "non_organic_fertilizer": ["nitrogen_applied", "nitrogen"],
    "lactating_cows_weight": ["weight", "body_weight"],
}

# Ponte ontologia → input_overrides do calculation_adapter
ONTOLOGY_TO_CALC_OVERRIDE: dict[str, dict[str, str]] = {
    "lactating_cows": {"kind": "headcount", "calc_key": "Lactating_Cows"},
    "dry_cows": {"kind": "headcount", "calc_key": "Dry_Cows"},
    "heifers": {"kind": "headcount", "calc_key": "Heifers"},
    "calves": {"kind": "headcount", "calc_key": "Calves"},
    "bulls": {"kind": "headcount", "calc_key": "Bulls"},
    "milk_production": {"kind": "milk_liters"},
    "milk": {"kind": "milk_liters"},
    "total_milk_production": {"kind": "milk_liters"},
    "non_organic_fertilizer": {"kind": "nitrogen_applied_kg"},
    "diesel": {"kind": "energy", "calc_key": "Diesel"},
    "electricity_grid": {"kind": "energy", "calc_key": "Electricity_Grid"},
    "gasoline": {"kind": "energy", "calc_key": "Gasoline"},
    "lactating_cows_weight": {"kind": "body_weight", "calc_key": "Lactating_Cows"},
    "weight": {"kind": "body_weight", "calc_key": "Lactating_Cows"},
}


def ontology_class_for(ontology_var: str) -> str:
    return VARIABLE_CLASS_MAP.get(ontology_var, "AdministrativeVariable")


def ontology_var_aliases(ontology_var: str) -> list[str]:
    aliases = list(ONTOLOGY_VAR_ALIASES.get(ontology_var, []))
    return [ontology_var] + aliases


def get_formula_requirements(formula_id: str) -> list[dict[str, str]]:
    """Variáveis ontológicas exigidas por fórmula (substitui catálogo legado)."""
    reqs = []
    for r in FORMULA_ONTOLOGY_REQUIREMENTS.get(formula_id, []):
        ov = r["ontology_var"]
        reqs.append({
            **r,
            "variable": ov,
            "ontology_class": ontology_class_for(ov),
        })
    return reqs
