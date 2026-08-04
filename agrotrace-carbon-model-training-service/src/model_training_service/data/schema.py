CANONICAL_COLUMNS = [
    "property_id",
    "period",
    "granularity",
    "lactating_cows",
    "milk_production_liters",
    "total_ghg_emissions_tco2e",
]

OPTIONAL_CONTROL_COLUMNS = ["approval_status", "publication_status"]

COLUMN_ALIASES = {
    "Property": "property_id",
    "property": "property_id",
    "Period": "period",
    "Granularity": "granularity",
    "Lactating_Cows": "lactating_cows",
    "Number_of_Lactating_Cows": "lactating_cows",
    "Milk_Production": "milk_production_liters",
    "Total_Milk_Production": "milk_production_liters",
    "Total_Emissions": "total_ghg_emissions_tco2e",
    "Total_GHG_Emissions_tCO2e": "total_ghg_emissions_tco2e",
}
