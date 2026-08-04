"""Gerador CSV mensal (monthly:v1) — sem colunas de emissão."""

from __future__ import annotations

import csv
import random
from io import StringIO
from typing import Any

from save_file.emulated.catalog import EmulatedFarmProfile
from save_file.emulated.generators._helpers import herd_for_month, milk_liters_monthly
from save_file.emulated.rng import derive_rng

# monthly:v1 — sem ef_enteric_kgCH4 / enteric_tCO2e (cálculo fica na pipeline)
MONTHLY_HEADER = [
    "Property",
    "Period",
    "Milk_Production",
    "Milk_Sales",
    "Milk_Gross_Price",
    "Number_of_Lactating_Cows",
    "Employees_During_the_Month",
    "Area_Used_for_Dairy_Activity",
    "Reproducers",
    "Lactating_Cows",
    "Dry_Cows",
    "Pregnant_Heifers",
    "Heifers_in_Raising",
    "Suckling_Calves_female",
    "Suckling_Calves_male",
    "Male_Calves_in_Raising",
    "Male_Calves_in_Fattening",
    "Draft_and_Breeding_Bulls",
    "Equines_and_Mules",
    "Number_of_Dry_Cows",
]


def build_monthly_row(
    profile: EmulatedFarmProfile,
    *,
    year: int,
    month: int,
    global_seed: int,
    alert_spike: bool = False,
) -> list[Any]:
    rng = derive_rng(global_seed, profile.property_id, year, month, "monthly")
    herd = herd_for_month(rng, profile, month)
    milk = milk_liters_monthly(
        rng, profile, month, herd.lactating,
        quality=profile.data_quality,
        alert_spike=alert_spike,
    )
    sales = round(milk * rng.uniform(0.93, 0.98), 1)
    price = round(rng.uniform(0.95, 1.05), 2)
    employees = max(3, herd.lactating // 4 + rng.randint(0, 3))
    area = round(profile.area_ha * rng.uniform(0.85, 1.05), 1)
    return [
        profile.property_id,
        f"{year}-{month:02d}-01",
        milk,
        sales,
        price,
        herd.lactating,
        employees,
        area,
        1 if month % 6 == 0 else 0,
        herd.lactating,
        herd.dry,
        herd.pregnant_heifers,
        herd.heifers_raising,
        herd.suckling_f,
        herd.suckling_m,
        herd.male_raising,
        herd.male_fattening,
        herd.draft_bulls,
        herd.equines,
        herd.dry,
    ]


def render_monthly_csv(
    profile: EmulatedFarmProfile,
    *,
    year: int,
    month: int,
    global_seed: int,
    alert_spike: bool = False,
) -> str:
    buf = StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(MONTHLY_HEADER)
    writer.writerow(
        build_monthly_row(
            profile, year=year, month=month, global_seed=global_seed, alert_spike=alert_spike
        )
    )
    return buf.getvalue()
