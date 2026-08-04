"""Gera CSVs determinísticos para o seed de ciclos pendentes."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

import config
from services.seed_period_planner import (
    SeedDataEntry,
    SeedScenarioPlan,
    all_data_entries,
    build_all_seed_plans,
    entry_to_dict,
)

SEED_DIR = config.SAMPLE_DATA_DIR / "seed"
MANIFEST_PATH = SEED_DIR / "manifest.json"

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
    "ef_enteric_kgCH4",
    "enteric_tCO2e",
]

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
    "Electricity_Grid",
    "Photovoltaic_Energy",
    "Pasture_Area",
    "Non_Organic_Fertilizer",
    "Organic_Fertilizer",
]

DAILY_TAGS = ("T1001", "T1002", "T1003", "T1004", "T1005")


def ensure_seed_dir() -> Path:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    return SEED_DIR


def _monthly_row(entry: SeedDataEntry) -> list[Any]:
    month = entry.month or 1
    year = entry.year or 2026
    seasonal = 1.0 + 0.08 * ((month - 1) % 12 - 6) / 6
    base_milk = 11800.0 + entry.index * 35
    milk = round(base_milk * seasonal + (month - 6) * 90, 1)
    cows = 20 + (month % 4) + (entry.index % 3)
    dry = 3 + (month % 2)
    heifers = 8 + (entry.index % 5)
    employees = 28 + (month % 3)
    area = round(42.0 + month * 0.4, 1)
    enteric = round(95000 + month * 480 + entry.index * 12, 1)
    enteric_tco2 = round(enteric * 0.028, 2)
    return [
        entry.property_id,
        f"{year}-{month:02d}-01",
        milk,
        round(milk * (0.95 + (month % 5) * 0.004), 1),
        round(0.98 + month * 0.002, 2),
        cows,
        employees,
        area,
        1 if month % 6 == 0 else 0,
        cows,
        dry,
        heifers // 2,
        heifers,
        2 + month % 3,
        1 + month % 2,
        month % 2,
        0 if month < 8 else 1,
        1,
        month % 3,
        dry,
        enteric,
        enteric_tco2,
    ]


def _annual_row(entry: SeedDataEntry) -> list[Any]:
    year = entry.year or 2021
    year_offset = year - 2021
    milk = round(205000 + year_offset * 4200 + entry.index * 800, 2)
    lactating = 26 + year_offset
    dry = 3 + (year_offset % 2)
    heifers = 10 + year_offset
    calves = 12 + (year_offset % 4)
    productivity = round(17.5 + year_offset * 0.35, 1)
    protein = round(3.18 + year_offset * 0.02, 2)
    fat = round(3.75 + year_offset * 0.03, 2)
    grass = round(75000 + year_offset * 2500, 1)
    grid = round(9500 + year_offset * 400, 1)
    solar = round(1500 + year_offset * 250, 1)
    pasture = round(38.0 + year_offset * 0.6, 1)
    return [
        entry.property_name,
        "Minas Gerais",
        f"Responsável {year}",
        f"Responsável {year}",
        "Latossolo" if year % 2 == 1 else "Argissolo",
        lactating,
        dry,
        heifers,
        calves,
        1 if year >= 2024 else 0,
        495.0 + year_offset * 3,
        525.0 + year_offset * 2,
        310.0 + year_offset * 4,
        145.0 + year_offset * 2,
        0.0,
        lactating + dry + heifers,
        calves,
        6 + year_offset,
        "venda" if year % 2 == 0 else "abate",
        productivity,
        milk,
        protein,
        fat,
        grass,
        round(4500 + year_offset * 300, 1),
        grid,
        solar,
        pasture,
        round(450 + year_offset * 40, 1),
        round(1100 + year_offset * 80, 1),
    ]


def _daily_rows(entry: SeedDataEntry) -> list[list[Any]]:
    day = entry.day or date(2026, 1, 1)
    day_num = (day - date(2026, 1, 1)).days
    rows: list[list[Any]] = []
    for offset, tag in enumerate(DAILY_TAGS):
        milk = round(42.0 + (day_num % 9) * 2.2 + offset * 1.8 + (entry.index % 7), 1)
        weight = round(615.0 + (day_num % 11) * 3.5 + offset * 5.0, 1)
        rows.append([day.isoformat(), tag, milk, weight])
    return rows


def build_monthly_entry_csv(entry: SeedDataEntry) -> Path:
    ensure_seed_dir()
    path = SEED_DIR / f"{entry.entry_id}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(MONTHLY_HEADER)
        writer.writerow(_monthly_row(entry))
    return path


def build_annual_entry_csv(entry: SeedDataEntry) -> Path:
    ensure_seed_dir()
    path = SEED_DIR / f"{entry.entry_id}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(ANNUAL_HEADER)
        writer.writerow(_annual_row(entry))
    return path


def build_daily_entry_csv(entry: SeedDataEntry) -> Path:
    ensure_seed_dir()
    path = SEED_DIR / f"{entry.entry_id}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Date", "Tag", "Milk", "Weight"])
        writer.writerows(_daily_rows(entry))
    return path


def build_entry_csv(entry: SeedDataEntry) -> Path:
    if entry.data_granularity == "monthly":
        return build_monthly_entry_csv(entry)
    if entry.data_granularity == "annual":
        return build_annual_entry_csv(entry)
    if entry.data_granularity == "daily":
        return build_daily_entry_csv(entry)
    raise ValueError(f"Granularidade desconhecida: {entry.data_granularity}")


def build_all_seed_files(plans: list[SeedScenarioPlan] | None = None) -> dict[str, Any]:
    """Gera 198 CSVs individuais e manifest.json."""
    plans = plans or build_all_seed_plans()
    ensure_seed_dir()
    manifest_entries: list[dict[str, Any]] = []
    paths: list[Path] = []

    for entry in all_data_entries(plans):
        path = build_entry_csv(entry)
        paths.append(path)
        manifest_entries.append({
            **entry_to_dict(entry),
            "path": str(path),
        })

    manifest = {
        "entry_count": len(manifest_entries),
        "approval_group_count": sum(len(p.approval_groups) for p in plans),
        "entries": manifest_entries,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "manifest_path": MANIFEST_PATH,
        "manifest": manifest,
        "paths": paths,
        "plans": plans,
    }
