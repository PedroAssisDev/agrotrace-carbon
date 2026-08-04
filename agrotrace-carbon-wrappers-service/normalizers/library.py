"""
Normalizadores — conversão de tipos e finalização por família de layout.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..core.field_mapping import map_schema_fields, to_snake_case
from ..temporal import date_to_iso
from ..validators.library import parse_decimal
from .harmonization import apply_layout_harmonization, strip_whitespace_strings

__all__ = [
    "apply_layout_harmonization",
    "finalize_annual_row",
    "finalize_intraday_row",
    "finalize_monthly_row",
    "map_schema_fields",
    "normalize_empty_to_none",
    "strip_whitespace_strings",
    "to_snake_case",
    "trim_string",
]


def trim_string(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def normalize_empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("", "na", "n/a", "-", "null"):
            return None
    return value


MONTHLY_NUMERIC_KEYS = frozenset(
    {
        "milk_production",
        "milk_sales",
        "milk_gross_price",
        "number_of_lactating_cows",
        "employees_during_the_month",
        "area_used_for_dairy_activity",
        "reproducers",
        "lactating_cows",
        "dry_cows",
        "pregnant_heifers",
        "heifers_in_raising",
        "suckling_calves_female",
        "suckling_calves_male",
        "male_calves_in_raising",
        "male_calves_in_fattening",
        "draft_and_breeding_bulls",
        "equines_and_mules",
        "number_of_dry_cows",
        "ef_enteric_kg_ch4",
        "enteric_tco2e",
    }
)


def finalize_intraday_row(row: dict[str, Any]) -> dict[str, Any] | None:
    d = row.get("_parsed_date")
    if d is None:
        return None
    date_str = date_to_iso(d) if isinstance(d, date) else str(row.get("date"))
    milk = parse_decimal(row.get("milk"))
    weight = parse_decimal(row.get("weight"))
    rec: dict[str, Any] = {
        "date": date_str,
        "animal_id": trim_string(row.get("animal_id")),
        "milk": float(milk) if milk is not None else None,
        "weight": float(weight) if weight is not None else None,
    }
    return rec


def finalize_monthly_row(row: dict[str, Any], period_start: date, period_end: str) -> dict[str, Any]:
    rec: dict[str, Any] = {}
    for k, v in row.items():
        if k.startswith("_"):
            continue
        if k in ("period_start", "period_end"):
            continue
        if v is None or (isinstance(v, str) and not v.strip()):
            rec[k] = None
            continue
        if k in MONTHLY_NUMERIC_KEYS:
            n = parse_decimal(v)
            rec[k] = float(n) if n is not None else None
        else:
            rec[k] = trim_string(v) if isinstance(v, str) else v
    rec["period_start"] = date_to_iso(period_start)
    rec["period_end"] = period_end
    return rec


def finalize_annual_row(row: dict[str, Any], year: int, numeric_fields: frozenset[str]) -> dict[str, Any]:
    rec: dict[str, Any] = {"year": year}
    for k, v in row.items():
        if k.startswith("_"):
            continue
        v = normalize_empty_to_none(v)
        if k in numeric_fields and v is not None:
            n = parse_decimal(v)
            rec[k] = float(n) if n is not None else None
        else:
            rec[k] = trim_string(v) if isinstance(v, str) else v
    return rec
