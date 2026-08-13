"""Importa CSVs Embrapa (pastas monthly/, annual/ e daily/) pela pipeline real.

Conjuntos independentes:
- monthly/: propriedades P-* (1 arquivo = 1 mês)
- annual/: propriedades BR-* (1 arquivo = 1 ano; year fixo 2022)
- daily/: propriedade D-1 (1 arquivo = 1 dia; aprovação consolidada por mês)
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import (
    LAYOUT_OPTIONS,
    SAVE_FILE_EMBRAPA_ANNUAL_DIR,
    SAVE_FILE_EMBRAPA_DAILY_DIR,
    SAVE_FILE_EMBRAPA_MONTHLY_DIR,
)
from services import local_orchestrator as orch
from services.farm_registry_service import ensure_farm
from utils.file_helpers import save_cycle

logger = logging.getLogger("agrotrace.embrapa_import")

ANNUAL_DEFAULT_YEAR = 2022
DAILY_DEFAULT_PROPERTY_ID = "D-1"
MONTH_LABELS_PT = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)

_MONTHLY_NAME_RE = re.compile(
    r"^monthly_report_(P-\d+)_(\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)
_ANNUAL_NAME_RE = re.compile(r"^annual_report_(BR)_?(\d+)\.csv$", re.IGNORECASE)
_DAILY_NAME_RE = re.compile(r"^daily_report_(\d{4}-\d{2}-\d{2})\.csv$", re.IGNORECASE)
_BR_ID_RE = re.compile(r"BR\s*[–\-]?\s*(\d+)", re.IGNORECASE)


@dataclass
class EmbrapaImportResult:
    cycles_created: list[dict] = field(default_factory=list)
    monthly_count: int = 0
    annual_count: int = 0
    daily_count: int = 0
    property_ids: list[str] = field(default_factory=list)


def _layout_id(layout_name: str) -> str:
    return LAYOUT_OPTIONS.get(layout_name, f"{layout_name}:v1")


def _read_csv_header_row(path: Path, delimiter: str = ";") -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        header = next(reader, [])
        row = next(reader, [])
    return header, row


def _month_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS_PT[month - 1]}/{year}"


def _normalize_br_property_id(raw: str) -> str:
    match = _BR_ID_RE.search(raw or "")
    if match:
        return f"BR-{int(match.group(1))}"
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (raw or "").strip().upper()).strip("-")
    return cleaned or "BR-UNKNOWN"


def _discover_monthly(directory: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("monthly_report_*.csv")):
        match = _MONTHLY_NAME_RE.match(path.name)
        if match:
            property_id = match.group(1).upper()
            period_date = match.group(2)
        else:
            header, row = _read_csv_header_row(path)
            by_col = dict(zip(header, row))
            property_id = (by_col.get("Property") or "").strip().upper()
            period_date = (by_col.get("Period") or "").strip()
            if not property_id or not period_date:
                logger.warning("Ignorando mensal sem Property/Period: %s", path.name)
                continue
        year_s, month_s, *_ = period_date.split("-")
        year, month = int(year_s), int(month_s)
        reporting_period = f"{year}-{month:02d}"
        items.append({
            "path": path,
            "property_id": property_id,
            "property_name": f"Embrapa {property_id}",
            "reporting_period": reporting_period,
            "cycle_id": f"EMBRAPA-{property_id}-{reporting_period}",
            "entry_id": f"EMBRAPA-{property_id}-{reporting_period}",
            "coverage_label": f"Embrapa mensal ({_month_label(year, month)})",
            "municipality": "",
            "state": "",
        })
    return items


def _discover_annual(directory: Path, *, year: int = ANNUAL_DEFAULT_YEAR) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("annual_report_*.csv")):
        header, row = _read_csv_header_row(path)
        by_col = dict(zip(header, row))
        raw_name = (by_col.get("Property_Name") or "").strip()
        match = _ANNUAL_NAME_RE.match(path.name)
        if match:
            property_id = f"BR-{int(match.group(2))}"
        elif raw_name:
            property_id = _normalize_br_property_id(raw_name)
        else:
            logger.warning("Ignorando anual sem Property_Name: %s", path.name)
            continue
        display_name = raw_name or f"Embrapa {property_id}"
        location = (by_col.get("Location") or "").strip()
        items.append({
            "path": path,
            "property_id": property_id,
            "property_name": display_name,
            "reporting_period": str(year),
            "cycle_id": f"EMBRAPA-{property_id}-{year}",
            "entry_id": f"EMBRAPA-{property_id}-{year}",
            "coverage_label": f"Embrapa anual ({year})",
            "municipality": location,
            "state": "SC" if "catarina" in location.casefold() else "",
        })
    return items


def _discover_daily(
    directory: Path,
    *,
    property_id: str = DAILY_DEFAULT_PROPERTY_ID,
) -> list[dict[str, Any]]:
    """Agrupa CSVs diários por mês (1 ciclo de aprovação / mês)."""
    day_files: list[tuple[str, Path]] = []
    if not directory.is_dir():
        return []
    for path in sorted(directory.glob("daily_report_*.csv")):
        match = _DAILY_NAME_RE.match(path.name)
        if match:
            day_iso = match.group(1)
        else:
            header, row = _read_csv_header_row(path, delimiter=",")
            by_col = dict(zip(header, row))
            day_iso = (by_col.get("Date") or "").strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", day_iso):
                logger.warning("Ignorando diário sem Date ISO: %s", path.name)
                continue
        day_files.append((day_iso, path))

    by_month: dict[str, list[tuple[str, Path]]] = {}
    for day_iso, path in day_files:
        by_month.setdefault(day_iso[:7], []).append((day_iso, path))

    items: list[dict[str, Any]] = []
    pid = (property_id or DAILY_DEFAULT_PROPERTY_ID).upper()
    for month_key, days in sorted(by_month.items()):
        year, month = int(month_key[:4]), int(month_key[5:7])
        payloads = [{
            "entry_id": f"EMBRAPA-{pid}-{day_iso}",
            "path": str(path),
            "reporting_period": day_iso,
            "property_id": pid,
            "original_filename": path.name,
        } for day_iso, path in days]
        items.append({
            "property_id": pid,
            "property_name": f"Embrapa {pid}",
            "reporting_period": month_key,
            "cycle_id": f"EMBRAPA-{pid}-{month_key}",
            "coverage_label": (
                f"Embrapa diário ({_month_label(year, month)} — {len(days)} dia(s))"
            ),
            "payloads": payloads,
            "municipality": "",
            "state": "",
        })
    return items


def _import_one(
    item: dict[str, Any],
    *,
    layout_name: str,
    data_granularity: str,
    approval_granularity: str,
    scenario_key: str,
) -> dict[str, Any]:
    ensure_farm(
        item["property_id"],
        item["property_name"],
        municipality=item.get("municipality", ""),
        state=item.get("state", ""),
        production_type="leite",
    )
    payloads = item.get("payloads") or [{
        "entry_id": item["entry_id"],
        "path": str(item["path"]),
        "reporting_period": item["reporting_period"],
        "property_id": item["property_id"],
        "original_filename": item["path"].name,
    }]
    cycle = orch.run_pipeline_group_until_pending(
        payloads,
        cycle_id=item["cycle_id"],
        property_id=item["property_id"],
        property_name=item["property_name"],
        reporting_period=item["reporting_period"],
        layout_name=layout_name,
        data_granularity=data_granularity,
        approval_granularity=approval_granularity,
        scenario_key=scenario_key,
        coverage_label=item.get("coverage_label"),
        layout_id=_layout_id(layout_name),
        frequency=data_granularity,
        uploaded_by="embrapa-import@agrotrace",
    )
    save_cycle(cycle)
    return cycle


def import_embrapa_uploads(
    *,
    monthly_dir: Path | None = None,
    annual_dir: Path | None = None,
    daily_dir: Path | None = None,
    annual_year: int = ANNUAL_DEFAULT_YEAR,
    include_monthly: bool = True,
    include_annual: bool = True,
    include_daily: bool = True,
) -> EmbrapaImportResult:
    """Importa pastas Embrapa até pendência de aprovação (sem wipe)."""
    monthly_dir = monthly_dir or SAVE_FILE_EMBRAPA_MONTHLY_DIR
    annual_dir = annual_dir or SAVE_FILE_EMBRAPA_ANNUAL_DIR
    daily_dir = daily_dir or SAVE_FILE_EMBRAPA_DAILY_DIR
    created: list[dict] = []
    property_ids: set[str] = set()
    monthly_count = 0
    annual_count = 0
    daily_count = 0

    if include_monthly:
        for item in _discover_monthly(monthly_dir):
            cycle = _import_one(
                item,
                layout_name="monthly",
                data_granularity="monthly",
                approval_granularity="monthly",
                scenario_key="embrapa_monthly",
            )
            created.append(cycle)
            property_ids.add(item["property_id"])
            monthly_count += 1
            logger.info("Embrapa mensal %s → %s", item["path"].name, cycle.get("cycle_id"))

    if include_annual:
        for item in _discover_annual(annual_dir, year=annual_year):
            cycle = _import_one(
                item,
                layout_name="annual",
                data_granularity="annual",
                approval_granularity="annual",
                scenario_key="embrapa_annual",
            )
            created.append(cycle)
            property_ids.add(item["property_id"])
            annual_count += 1
            logger.info("Embrapa anual %s → %s", item["path"].name, cycle.get("cycle_id"))

    if include_daily:
        for item in _discover_daily(daily_dir):
            cycle = _import_one(
                item,
                layout_name="intraday",
                data_granularity="daily",
                approval_granularity="monthly",
                scenario_key="embrapa_daily",
            )
            created.append(cycle)
            property_ids.add(item["property_id"])
            daily_count += 1
            logger.info("Embrapa diário %s → %s", item["cycle_id"], cycle.get("cycle_id"))

    return EmbrapaImportResult(
        cycles_created=created,
        monthly_count=monthly_count,
        annual_count=annual_count,
        daily_count=daily_count,
        property_ids=sorted(property_ids),
    )
