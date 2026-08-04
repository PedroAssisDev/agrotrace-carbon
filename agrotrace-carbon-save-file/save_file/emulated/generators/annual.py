"""Gerador CSV anual (annual:v1) — 68 colunas, sem Total GHG."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from save_file.emulated.catalog import EmulatedFarmProfile
from save_file.emulated.generators._helpers import effective_lactating, herd_for_month
from save_file.emulated.rng import derive_rng, jitter

ANNUAL_HEADER = [
    "Property_Name",
    "Location",
    "Owner_Name",
    "Information_Responsible",
    "Predominant_Soil_Type",
    "Lactating_Cows",
    "Dry_Cows",
    "Heifers",
    "Calves",
    "Bulls",
    "Lactating_Cows_Weight",
    "Dry_Cows_Weight",
    "Heifers_Weight",
    "Calves_Weight",
    "Bulls_Weight",
    "Females",
    "Males",
    "Cows_Discarded_Per_Year",
    "Discarded_Cows_Destination",
    "Productivity",
    "Total_Milk_Production",
    "Milk_Protein_Percentage",
    "Milk_Fat_Percentage",
    "Grass_Fresh",
    "Grass_Hay_On_Farm",
    "Grass_Hay_Off_Farm",
    "Grass_Silage_On_Or_Off_Farm",
    "Maize_Silage",
    "Lucerne_Alfalfa_Silage",
    "Other_Fodder",
    "Straw_Peanut_Hull_Others",
    "Crop_Residues",
    "Hay_Oat_Clover",
    "Sorghum_Silage",
    "Wheat",
    "Barley",
    "Maize_Grain",
    "Oats",
    "Rice",
    "Rye",
    "Sorghum",
    "Other_Cereals",
    "DDG",
    "Soybean_Meal_Hull",
    "Sugarbeet_Molasses",
    "Whey_Powder",
    "Rapeseed_Cake_Meal",
    "Sunflower_Cake_Meal",
    "Cottonseed_Cake_Meal",
    "Beans_Peas",
    "Cassava_Tapioca",
    "Other_Feed",
    "Milk_Powder_Dry_Matter",
    "Citrus_Pulp",
    "Mineral_Mix",
    "Lucerne_Alfalfa_Hay",
    "Brewers_Grain_Brewery_Residue",
    "Total",
    "DMI_Check",
    "Diesel",
    "Gasoline",
    "Other_Fuel",
    "Electricity_Grid",
    "Photovoltaic_Energy",
    "Pasture_Area",
    "Non_Organic_Fertilizer",
    "Organic_Fertilizer",
]

# Índices de colunas feed para soma DMI (sem Total como emissão)
_FEED_START = ANNUAL_HEADER.index("Grass_Fresh")
_FEED_END = ANNUAL_HEADER.index("Brewers_Grain_Brewery_Residue") + 1


def _feed_values(
    rng,
    profile: EmulatedFarmProfile,
    lactating: int,
    *,
    incomplete: bool,
) -> list[float]:
    scale = 1.0
    if profile.herd_scale == "small":
        scale = 0.55
    elif profile.herd_scale == "large":
        scale = 1.45
    base_grass = 45000 * scale + lactating * 800
    feeds = [
        round(jitter(rng, base_grass, 0.12), 1),  # Grass_Fresh
        round(jitter(rng, 4500 * scale, 0.15), 1),
        round(jitter(rng, 1200 * scale, 0.2), 1),
        round(jitter(rng, 6800 * scale, 0.1), 1),
        round(jitter(rng, 95000 * scale, 0.1), 1),  # Maize_Silage
        round(jitter(rng, 2200 * scale, 0.15), 1),
        round(jitter(rng, 1800 * scale, 0.15), 1),
        round(jitter(rng, 3200 * scale, 0.12), 1),
        round(jitter(rng, 2100 * scale, 0.12), 1),
        round(jitter(rng, 1500 * scale, 0.12), 1),
        round(jitter(rng, 900 * scale, 0.15), 1),
        round(jitter(rng, 1100 * scale, 0.15), 1),
        round(jitter(rng, 800 * scale, 0.15), 1),
        round(jitter(rng, 700 * scale, 0.15), 1),
        round(jitter(rng, 600 * scale, 0.15), 1),
        round(jitter(rng, 2400 * scale, 0.12), 1),
        round(jitter(rng, 1800 * scale, 0.12), 1),
        round(jitter(rng, 500 * scale, 0.2), 1),
        round(jitter(rng, 400 * scale, 0.2), 1),
        round(jitter(rng, 350 * scale, 0.2), 1),
        round(jitter(rng, 12000 * scale, 0.1), 1),  # DDG
        round(jitter(rng, 8500 * scale, 0.1), 1),
        round(jitter(rng, 2200 * scale, 0.15), 1),
        round(jitter(rng, 900 * scale, 0.15), 1),
        round(jitter(rng, 1100 * scale, 0.15), 1),
        round(jitter(rng, 750 * scale, 0.15), 1),
        round(jitter(rng, 650 * scale, 0.15), 1),
        round(jitter(rng, 500 * scale, 0.15), 1),
        round(jitter(rng, 400 * scale, 0.15), 1),
        round(jitter(rng, 300 * scale, 0.2), 1),
        round(jitter(rng, 1800 * scale, 0.12), 1),
        round(jitter(rng, 950 * scale, 0.12), 1),
        round(jitter(rng, 1200 * scale, 0.12), 1),
    ]
    if incomplete:
        # Zera fertilizantes/energia parcialmente via zeros em posições específicas no row builder
        for i in (10, 15, 20):
            if i < len(feeds):
                feeds[i] = 0.0
    return feeds


def build_annual_row(
    profile: EmulatedFarmProfile,
    *,
    year: int,
    global_seed: int,
) -> list[Any]:
    rng = derive_rng(global_seed, profile.property_id, year, "annual")
    herd = herd_for_month(rng, profile, 6)
    lactating = effective_lactating(profile) + (year - 2021)
    dry = max(2, lactating // 7)
    heifers = max(6, lactating // 2)
    calves = max(5, heifers // 2)
    bulls = 1 if lactating > 28 else 0
    milk_total = round(lactating * jitter(rng, 7800, 0.08) * 12, 2)
    productivity = round(milk_total / max(lactating, 1) / 365, 2)
    protein = round(jitter(rng, 3.18 + (year - 2021) * 0.02, 0.02), 2)
    fat = round(jitter(rng, 3.75 + (year - 2021) * 0.03, 0.02), 2)
    feeds = _feed_values(rng, profile, lactating, incomplete=profile.data_quality == "incomplete")
    dmi_sum = round(sum(feeds), 1)
    diesel = round(jitter(rng, profile.area_ha * 18, 0.15), 1)
    gasoline = round(jitter(rng, profile.area_ha * 2.5, 0.2), 1)
    other_fuel = round(jitter(rng, 200, 0.3), 1)
    grid = round(jitter(rng, lactating * 380, 0.12), 1)
    solar = round(jitter(rng, lactating * 55, 0.2), 1)
    pasture = round(profile.area_ha * rng.uniform(0.55, 0.75), 1)
    if profile.data_quality == "incomplete":
        grid = 0.0
        solar = 0.0
    non_org = round(jitter(rng, 420 + (year - 2021) * 35, 0.15), 1)
    organic = round(jitter(rng, 1100 + (year - 2021) * 80, 0.12), 1)
    if profile.data_quality == "incomplete":
        non_org = 0.0
        organic = 0.0

    row: list[Any] = [
        profile.name,
        f"{profile.municipality}, {profile.state}",
        f"Responsável {year}",
        f"Responsável {year}",
        "Latossolo" if year % 2 == 1 else "Argissolo",
        lactating,
        dry,
        heifers,
        calves,
        bulls,
        round(jitter(rng, 495, 0.03), 1),
        round(jitter(rng, 525, 0.03), 1),
        round(jitter(rng, 310, 0.04), 1),
        round(jitter(rng, 145, 0.04), 1),
        0.0,
        lactating + dry + heifers,
        calves,
        max(4, lactating // 5),
        "venda" if year % 2 == 0 else "abate",
        productivity,
        milk_total,
        protein,
        fat,
        *feeds,
        dmi_sum,  # Total — DMI agregado, não CO2e
        dmi_sum,  # DMI_Check
        diesel,
        gasoline,
        other_fuel,
        grid,
        solar,
        pasture,
        non_org,
        organic,
    ]
    return row


def render_annual_csv(
    profile: EmulatedFarmProfile,
    *,
    year: int,
    global_seed: int,
) -> str:
    buf = StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(ANNUAL_HEADER)
    writer.writerow(build_annual_row(profile, year=year, global_seed=global_seed))
    return buf.getvalue()
