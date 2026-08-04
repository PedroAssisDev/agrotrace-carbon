"""Internal catalogs: canonical variables, units, gases, methods, software."""

from __future__ import annotations

from typing import Any

from ontology import iri as iri_mod
from ontology.mappings import VARIABLE_CLASS_MAP


def _var_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for name, cls_name in sorted(VARIABLE_CLASS_MAP.items()):
        entries.append({
            "name": name,
            "class": cls_name,
            "display": name.replace("_", " ").title(),
            "original_column": name,
        })
    return entries


CANONICAL_VARIABLES: list[dict[str, str]] = _var_entries()

UNITS: list[dict[str, str]] = [
    {"name": "head", "display": "Head (animals)"},
    {"name": "kg", "display": "Kilogram"},
    {"name": "liter", "display": "Liter"},
    {"name": "hectare", "display": "Hectare"},
    {"name": "percentage", "display": "Percentage"},
    {"name": "kWh", "display": "Kilowatt-hour"},
    {"name": "liter_fuel", "display": "Liter of fuel"},
    {"name": "kg_ch4", "display": "Kilogram CH4"},
    {"name": "kg_n2o", "display": "Kilogram N2O"},
    {"name": "kg_co2", "display": "Kilogram CO2"},
    {"name": "kg_co2e", "display": "Kilogram CO2 equivalent"},
    {"name": "tonne_co2e", "display": "Tonne CO2 equivalent"},
    {"name": "liter_per_day", "display": "Liter per day"},
    {"name": "liter_per_month", "display": "Liter per month"},
    {"name": "liter_per_year", "display": "Liter per year"},
    {"name": "kg_per_day", "display": "Kilogram per day"},
    {"name": "kg_per_month", "display": "Kilogram per month"},
    {"name": "kg_per_year", "display": "Kilogram per year"},
    {"name": "kg_dm_per_day", "display": "Kilogram DM per day"},
    {"name": "mj_per_kg_dm", "display": "MJ per kg DM"},
    {"name": "kg_ch4_per_head_month", "display": "kg CH4 per head per month"},
    {"name": "kg_ch4_per_head_year", "display": "kg CH4 per head per year"},
    {"name": "currency", "display": "Currency"},
    {"name": "dimensionless", "display": "Dimensionless"},
    {"name": "text", "display": "Text"},
]

GREENHOUSE_GASES = [
    {"name": "carbon_dioxide", "class": "CarbonDioxide", "symbol": "CO2"},
    {"name": "methane", "class": "Methane", "symbol": "CH4"},
    {"name": "nitrous_oxide", "class": "NitrousOxide", "symbol": "N2O"},
]

EMISSION_SOURCES = [
    {"name": "enteric_fermentation", "class": "EntericFermentation"},
    {"name": "manure_management", "class": "ManureManagement"},
    {"name": "fertilizer_application", "class": "FertilizerApplication"},
    {"name": "energy_use", "class": "EnergyUse"},
    {"name": "total_ghg", "class": "TotalGHG"},
]

CALCULATION_METHODS: list[dict[str, Any]] = [
    {
        "name": "calculate_enteric_fermentation_ch4",
        "class": "EntericFermentationCH4CalculationMethod",
        "function_name": "calculate_enteric_fermentation_ch4",
        "module_path": "emissions/enteric_fermentation.py",
        "gas": "methane",
        "emission_source": "enteric_fermentation",
        "required_variables": [
            "lactating_cows", "dry_cows", "bulls", "calves", "ef_enteric_kg_ch4",
        ],
        "result_unit": "kg_ch4",
        "software_component": "enteric_fermentation_component",
    },
    {
        "name": "calculate_manure_management_ch4",
        "class": "ManureManagementCH4CalculationMethod",
        "function_name": "calculate_manure_management_ch4",
        "module_path": "emissions/manure_management.py",
        "gas": "methane",
        "emission_source": "manure_management",
        "required_variables": ["lactating_cows", "dry_cows", "heifers", "calves"],
        "result_unit": "kg_ch4",
        "software_component": "manure_management_component",
    },
    {
        "name": "calculate_fertilizer_n2o",
        "class": "FertilizerN2OCalculationMethod",
        "function_name": "calculate_fertilizer_n2o",
        "module_path": "emissions/fertilizer.py",
        "gas": "nitrous_oxide",
        "emission_source": "fertilizer_application",
        "required_variables": ["organic_fertilizer", "non_organic_fertilizer"],
        "result_unit": "kg_n2o",
        "software_component": "fertilizer_component",
    },
    {
        "name": "calculate_energy_co2",
        "class": "EnergyCO2CalculationMethod",
        "function_name": "calculate_energy_co2",
        "module_path": "emissions/energy.py",
        "gas": "carbon_dioxide",
        "emission_source": "energy_use",
        "required_variables": [
            "diesel", "gasoline", "other_fuel", "electricity_grid", "photovoltaic_energy",
        ],
        "result_unit": "kg_co2",
        "software_component": "energy_component",
    },
    {
        "name": "calculate_total_ghg_co2e",
        "class": "TotalGHGCO2eCalculationMethod",
        "function_name": "calculate_total_ghg_co2e",
        "module_path": "emissions/ghg_total.py",
        "emission_source": "total_ghg",
        "required_variables": ["enteric_ch4", "manure_ch4", "fertilizer_n2o", "energy_co2"],
        "requires_gwp_parameter_set": True,
        "result_unit": "kg_co2e",
        "software_component": "ghg_total_component",
    },
    {
        "name": "monthly_to_annual_sum",
        "class": "MonthlyToAnnualSumMethod",
        "function_name": "sum_monthly_values",
        "module_path": "emissions/conversion_helpers.py",
        "result_unit": "dimensionless",
        "software_component": "conversion_helpers_component",
    },
    {
        "name": "monthly_to_annual_proration",
        "class": "MonthlyToAnnualProrationMethod",
        "function_name": "uniform_monthly_from_yearly_per_animal",
        "module_path": "emissions/conversion_helpers.py",
        "result_unit": "dimensionless",
        "software_component": "conversion_helpers_component",
    },
    {
        "name": "legacy_default_configuration_provider",
        "class": "DefaultConfigurationProvider",
        "function_name": "default_enteric_ch4_kg_per_animal_yearly",
        "module_path": "emissions/defaults.py",
        "result_unit": "dimensionless",
        "software_component": "defaults_component",
    },
    {
        "name": "batch_runner",
        "class": "BatchCalculationRunner",
        "function_name": "compute_row_results",
        "module_path": "batch_runner.py",
        "result_unit": "dimensionless",
        "software_component": "batch_runner_component",
    },
    {
        "name": "environmental_calcs_adapter",
        "class": "LegacyCompatibilityAdapter",
        "function_name": "calculate_total_emissions",
        "module_path": "environmental_calcs.py",
        "result_unit": "dimensionless",
        "software_component": "environmental_calcs_adapter",
        "compatibility_mode": "legacy",
    },
]

SOFTWARE_COMPONENTS: list[dict[str, str]] = [
    {"name": "enteric_fermentation_component", "module_path": "emissions/enteric_fermentation.py"},
    {"name": "manure_management_component", "module_path": "emissions/manure_management.py"},
    {"name": "fertilizer_component", "module_path": "emissions/fertilizer.py"},
    {"name": "energy_component", "module_path": "emissions/energy.py"},
    {"name": "ghg_total_component", "module_path": "emissions/ghg_total.py"},
    {"name": "conversion_helpers_component", "module_path": "emissions/conversion_helpers.py"},
    {"name": "defaults_component", "module_path": "emissions/defaults.py"},
    {"name": "batch_runner_component", "module_path": "batch_runner.py"},
    {"name": "environmental_calcs_adapter", "module_path": "environmental_calcs.py"},
]

GWP_PARAMETER_SET_EXAMPLE = {
    "name": "gwp_ipcc_ar4_default",
    "description": (
        "GWP IPCC AR4 (caixa de ferramentas EcoFarm) — valores injetáveis no cálculo; "
        "fonte alinhada a emissions.defaults.gwp_ipcc_ar4."
    ),
    "gwp_ch4": 25.0,
    "gwp_n2o": 298.0,
    "gwp_co2": 1.0,
}

# Espelhos numéricos de emissions.defaults (fonte de documentação semântica na ontologia).
# Mantidos aqui para o ontology-manager não depender do calculation-service no import.
_DEFAULT_ENTERIC_YEARLY = {
    "Lactating_Cows": 100.0,
    "Dry_Cows": 50.0,
    "Heifers": 30.0,
    "Calves": 20.0,
    "Bulls": 10.0,
}
_DEFAULT_MANURE_MD = {
    "Lactating_Cows": 0.08,
    "Dry_Cows": 0.07,
    "Heifers": 0.06,
    "Calves": 0.05,
    "Bulls": 0.09,
}
# Espelho de emissions.defaults.default_manure_ch4_kg_per_kg_manure (recalibrado).
_DEFAULT_MANURE_EF = {
    "Lactating_Cows": 0.001,
    "Dry_Cows": 0.0008,
    "Heifers": 0.0007,
    "Calves": 0.0006,
    "Bulls": 0.0012,
}
_DEFAULT_ENERGY = {
    "Diesel": 2.68,
    "Gasoline": 2.31,
    "Electricity_Grid": 0.233,
    "Photovoltaic_Energy": 0.0,
}
_DEFAULT_FERTILIZER = {
    "direct_n2o_emission_factor": 0.01,
    "indirect_n2o_emission_factor": 0.005,
    "fraction_n_volatilized": 0.1,
}


def _get_class(onto: object, class_name: str) -> type:
    return getattr(onto, class_name)


def _add_emission_factor(
    onto: object,
    *,
    group: str,
    key: str,
    value: float,
    unit_name: str | None,
    unit_individuals: dict[str, object],
) -> object:
    ind = _get_class(onto, "EmissionFactor")(
        iri_mod.individual_name("ef", f"{group}_{key}")
    )
    ind.label = [f"{group}:{key}"]
    ind.hasParameterName = [f"{group}:{key}"]
    ind.hasParameterValue = [float(value)]
    ind.hasParameterLifecycleStatus = ["pending"]
    if unit_name and unit_name in unit_individuals:
        ind.hasUnit = [unit_individuals[unit_name]]
    return ind


def populate_catalogs(onto: object) -> None:
    """Instantiate catalog individuals in the ontology."""
    with onto:
        # Units
        unit_individuals: dict[str, object] = {}
        for u in UNITS:
            ind = _get_class(onto, "Unit")(iri_mod.individual_name("unit", u["name"]))
            ind.label = [u["display"]]
            ind.hasCanonicalName = [u["name"]]
            unit_individuals[u["name"]] = ind

        # Canonical variables
        var_individuals: dict[str, object] = {}
        for v in CANONICAL_VARIABLES:
            cls = _get_class(onto, v["class"])
            ind = cls(iri_mod.individual_name("var", v["name"]))
            ind.label = [v["display"]]
            ind.hasCanonicalName = [v["name"]]
            ind.hasDisplayName = [v["display"]]
            ind.hasOriginalColumnName = [v["original_column"]]
            var_individuals[v["name"]] = ind

        # Greenhouse gases
        gas_individuals: dict[str, object] = {}
        for g in GREENHOUSE_GASES:
            cls = _get_class(onto, g["class"])
            ind = cls(iri_mod.individual_name("gas", g["name"]))
            ind.label = [g["symbol"]]
            ind.hasCanonicalName = [g["name"]]
            gas_individuals[g["name"]] = ind

        # Emission sources
        source_individuals: dict[str, object] = {}
        for s in EMISSION_SOURCES:
            cls = _get_class(onto, s["class"])
            ind = cls(iri_mod.individual_name("source", s["name"]))
            ind.label = [s["name"].replace("_", " ").title()]
            ind.hasCanonicalName = [s["name"]]
            source_individuals[s["name"]] = ind

        # Software components
        sw_individuals: dict[str, object] = {}
        for sw in SOFTWARE_COMPONENTS:
            ind = _get_class(onto, "SoftwareComponent")(
                iri_mod.individual_name("sw", sw["name"])
            )
            ind.label = [sw["name"]]
            ind.hasModulePath = [sw["module_path"]]
            sw_individuals[sw["name"]] = ind

        # GWP IPCC AR4 (valores canônicos alinhados ao calculation-service)
        gwp = _get_class(onto, "GWPParameterSet")(
            iri_mod.individual_name("gwp", GWP_PARAMETER_SET_EXAMPLE["name"])
        )
        gwp.label = [GWP_PARAMETER_SET_EXAMPLE["name"]]
        gwp.hasMethodDescription = [GWP_PARAMETER_SET_EXAMPLE["description"]]
        gwp.hasGWP_CH4 = [GWP_PARAMETER_SET_EXAMPLE["gwp_ch4"]]
        gwp.hasGWP_N2O = [GWP_PARAMETER_SET_EXAMPLE["gwp_n2o"]]
        gwp.hasGWP_CO2 = [GWP_PARAMETER_SET_EXAMPLE["gwp_co2"]]
        gwp.hasParameterLifecycleStatus = ["pending"]
        gwp.hasParameterName = ["gwp_set"]

        # EmissionFactor individuals (defaults Tier-1 / EcoFarm)
        ef_individuals: list[object] = []
        for key, value in _DEFAULT_ENTERIC_YEARLY.items():
            ef_individuals.append(
                _add_emission_factor(
                    onto,
                    group="enteric",
                    key=key,
                    value=value,
                    unit_name="kg_ch4_per_head_year",
                    unit_individuals=unit_individuals,
                )
            )
        for key, value in _DEFAULT_MANURE_MD.items():
            ef_individuals.append(
                _add_emission_factor(
                    onto,
                    group="manure_md",
                    key=key,
                    value=value,
                    unit_name=None,
                    unit_individuals=unit_individuals,
                )
            )
        for key, value in _DEFAULT_MANURE_EF.items():
            ef_individuals.append(
                _add_emission_factor(
                    onto,
                    group="manure_ef",
                    key=key,
                    value=value,
                    unit_name=None,
                    unit_individuals=unit_individuals,
                )
            )
        for key, value in _DEFAULT_ENERGY.items():
            ef_individuals.append(
                _add_emission_factor(
                    onto,
                    group="energy",
                    key=key,
                    value=value,
                    unit_name=None,
                    unit_individuals=unit_individuals,
                )
            )
        for key, value in _DEFAULT_FERTILIZER.items():
            ef_individuals.append(
                _add_emission_factor(
                    onto,
                    group="fertilizer",
                    key=key,
                    value=value,
                    unit_name=None,
                    unit_individuals=unit_individuals,
                )
            )

        # Calculation methods
        for m in CALCULATION_METHODS:
            cls = _get_class(onto, m["class"])
            ind = cls(iri_mod.individual_name("method", m["name"]))
            ind.label = [m["name"]]
            ind.hasFunctionName = [m["function_name"]]
            ind.hasModulePath = [m["module_path"]]
            if m.get("result_unit"):
                ind.hasResultUnit = [m["result_unit"]]
            if m.get("requires_gwp_parameter_set"):
                ind.requiresGWPParameterSet = [True]
                ind.usesGWPParameterSet = [gwp]
            if m.get("compatibility_mode"):
                ind.hasCompatibilityMode = [m["compatibility_mode"]]
            if m.get("gas"):
                ind.calculatesGas = [gas_individuals[m["gas"]]]
            if m.get("emission_source"):
                ind.calculatesEmissionSource = [source_individuals[m["emission_source"]]]
            sw = sw_individuals.get(m.get("software_component", ""))
            if sw:
                ind.implementedInSoftwareComponent = [sw]
            fn = _get_class(onto, "SoftwareFunction")(
                iri_mod.individual_name("fn", m["function_name"])
            )
            fn.hasFunctionName = [m["function_name"]]
            fn.hasModulePath = [m["module_path"]]
            if sw:
                fn.implementedInSoftwareComponent = [sw]
            ind.implementedByFunction = [fn]
            for rv in m.get("required_variables", []):
                if rv in var_individuals:
                    ind.requiresInputVariable.append(var_individuals[rv])

    onto._catalog_cache = {  # type: ignore[attr-defined]
        "units": unit_individuals,
        "variables": var_individuals,
        "gases": gas_individuals,
        "sources": source_individuals,
        "software": sw_individuals,
        "emission_factors_count": len(ef_individuals),
    }


def get_catalog_individual(onto: object, kind: str, name: str) -> object | None:
    cache = getattr(onto, "_catalog_cache", {})
    return cache.get(kind, {}).get(name)
