"""Serviço central de opções para o filtro global (propriedade + período)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from config import EVIDENCE_PACKAGES_DIR, RAW_ORIGINALS_DIR, SAVE_FILE_ORIGINALS_DIR
from services.property_registry import load_property_catalog
from utils.file_helpers import list_cycles
from utils.property_filter import get_all_property_ids, normalize_property_id

logger = logging.getLogger("agrotrace.filter")

_PERIOD_RE = re.compile(r"^(\d{4}-\d{2})$")
_FILENAME_PERIOD_RE = re.compile(r"^[A-Za-z0-9_-]+_(\d{4}-\d{2})_")


def _normalize_period_value(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    return value if _PERIOD_RE.match(value) else None


def _periods_from_record(record: dict) -> set[str]:
    periods: set[str] = set()
    for key in ("reporting_period", "period"):
        p = _normalize_period_value(record.get(key))
        if p:
            periods.add(p)
    raw = record.get("raw_file")
    if isinstance(raw, dict):
        p = _normalize_period_value(raw.get("reporting_period") or raw.get("period"))
        if p:
            periods.add(p)
    evidence = record.get("evidence_package")
    if isinstance(evidence, dict):
        p = _normalize_period_value(evidence.get("reporting_period") or evidence.get("period"))
        if p:
            periods.add(p)
    return periods


def get_available_properties() -> list[dict[str, Any]]:
    """Propriedades disponíveis: mock + derivadas de dados locais."""
    return load_property_catalog()


def get_available_periods(farm_id: str | None = None) -> list[str]:
    """Períodos únicos, opcionalmente filtrados pela fazenda selecionada."""
    wanted = {farm_id} if farm_id else None
    periods: set[str] = set()

    for cycle in list_cycles():
        if wanted is not None and not (wanted & get_all_property_ids(cycle)):
            continue
        periods.update(_periods_from_record(cycle))
        rp = cycle.get("reporting_period")
        if isinstance(rp, str) and rp.strip() and "/" in rp:
            periods.add(rp.strip())

    if EVIDENCE_PACKAGES_DIR.exists():
        for path in EVIDENCE_PACKAGES_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if wanted is not None and not (wanted & get_all_property_ids(data)):
                continue
            periods.update(_periods_from_record(data))

    for originals_dir in (SAVE_FILE_ORIGINALS_DIR, RAW_ORIGINALS_DIR):
        if not originals_dir.exists():
            continue
        for path in originals_dir.glob("*"):
            match = _FILENAME_PERIOD_RE.match(path.name)
            if not match:
                continue
            if wanted is not None:
                pid_match = re.match(r"^([A-Za-z0-9_-]+)_\d{4}-\d{2}_", path.name)
                if pid_match and pid_match.group(1) not in wanted:
                    continue
            periods.add(match.group(1))

    if not periods and farm_id:
        return []

    return sorted(periods, reverse=True)


def infer_granularity_for_farm(farm_id: str | None) -> str:
    """Inferência de granularidade a partir dos ciclos da fazenda."""
    if not farm_id:
        return "monthly"
    from utils.global_filter import cycle_granularity, cycles_for_farm

    farm_cycles = cycles_for_farm(list_cycles(), farm_id)
    if farm_cycles:
        preferred = max(farm_cycles, key=lambda c: c.get("updated_at") or c.get("created_at") or "")
        return cycle_granularity(preferred)
    if "ANNUAL" in farm_id.upper():
        return "annual"
    if "DAILY" in farm_id.upper():
        return "daily"
    return "monthly"


def cycles_for_farm_service(farm_id: str | None) -> list[dict]:
    from utils.global_filter import cycles_for_farm

    return cycles_for_farm(list_cycles(), farm_id)


def get_available_filter_options(
    farm_id: str | None = None,
    preferred_cycle_id: str | None = None,
) -> dict[str, Any]:
    """Retorna propriedades e ciclos disponíveis para os controles de filtro."""
    from utils.global_filter import (
        analysis_period_dropdown_options,
        analysis_scenario_cycles,
        cycle_dropdown_options,
        cycles_for_farm,
        pick_default_cycle,
    )

    all_cycles = list_cycles()
    farm_cycles = cycles_for_farm(all_cycles, farm_id) if farm_id else []
    active = pick_default_cycle(farm_cycles, preferred_cycle_id) if farm_cycles else None
    scenario = (
        analysis_scenario_cycles(all_cycles, {"farm_id": farm_id}, active)
        if farm_id else []
    )
    analysis_periods = analysis_period_dropdown_options(scenario)
    logger.debug(
        "[FILTER] get_available_filter_options farm=%s cycles=%d analysis_periods=%s",
        farm_id,
        len(farm_cycles),
        [p.get("value") for p in analysis_periods],
    )
    return {
        "properties": get_available_properties(),
        "cycles": cycle_dropdown_options(farm_cycles),
        "periods": get_available_periods(farm_id),
        "analysis_periods": analysis_periods,
    }


def refresh_filter_options(global_filter: dict[str, Any] | None) -> dict[str, Any]:
    """Recarrega opções conforme a fazenda selecionada no filtro."""
    from utils.global_filter import get_farm_id

    gf = global_filter or {}
    return get_available_filter_options(get_farm_id(gf), gf.get("cycle_id"))
