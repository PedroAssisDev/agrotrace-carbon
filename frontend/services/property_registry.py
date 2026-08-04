"""Catálogo de propriedades do frontend.

Combina propriedades mock fixas com propriedades derivadas dos ciclos já
persistidos em ``frontend/data/`` e dos pacotes de evidência. Não toca nos
serviços externos — apenas lê dados locais.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import re

import config
from config import EVIDENCE_PACKAGES_DIR, RAW_ORIGINALS_DIR
from utils.file_helpers import list_cycles
from utils.property_filter import get_all_property_ids

logger = logging.getLogger("agrotrace.property_registry")


# Propriedades mock fixas para a demonstração multi-propriedade.
MOCK_PROPERTIES: list[dict[str, Any]] = [
    {
        "property_id": "FARM-MONTHLY-001",
        "name": "Fazenda Boa Vista Leiteira",
        "municipality": "Uberaba",
        "state": "MG",
    },
    {
        "property_id": "FARM-ANNUAL-001",
        "name": "Fazenda Santa Clara Sustentável",
        "municipality": "Patos de Minas",
        "state": "MG",
    },
    {
        "property_id": "FARM-DAILY-001",
        "name": "Fazenda Experimental Sensorial",
        "municipality": "Rio Verde",
        "state": "GO",
    },
    {
        "property_id": "FARM-001",
        "name": "Fazenda Santa Clara",
        "municipality": "Patos de Minas",
        "state": "MG",
    },
    {
        "property_id": "FARM-002",
        "name": "Fazenda Boa Vista",
        "municipality": "Uberaba",
        "state": "MG",
    },
    {
        "property_id": "FARM-003",
        "name": "Fazenda São João",
        "municipality": "Rio Verde",
        "state": "GO",
    },
]

# Aliases de IDs legados conhecidos (ex.: scripts de validação usam "P-1").
LEGACY_ALIASES: dict[str, str] = {
    "P-1": "FARM-001",
}


def _entry(property_id: str, name: str | None = None, municipality: str = "", state: str = "") -> dict[str, Any]:
    return {
        "property_id": property_id,
        "name": name or property_id,
        "municipality": municipality,
        "state": state,
    }


def _add_found(found: dict[str, dict[str, Any]], pid: str, name: str | None = None) -> None:
    canonical = LEGACY_ALIASES.get(pid, pid)
    if canonical not in found:
        found[canonical] = _entry(canonical, name)
    elif name and (not found[canonical].get("name") or found[canonical]["name"] == canonical):
        found[canonical]["name"] = name


def _derive_from_cycles() -> dict[str, dict[str, Any]]:
    """Extrai propriedades únicas dos ciclos salvos (topo + campos aninhados)."""
    found: dict[str, dict[str, Any]] = {}
    for c in list_cycles():
        for pid in get_all_property_ids(c):
            _add_found(found, pid, c.get("property_name"))
    return found


def _derive_from_raw_originals() -> dict[str, dict[str, Any]]:
    """Extrai property_id dos nomes de arquivo em raw_originals (ex.: FARM-REAL_2026-03_*.csv)."""
    found: dict[str, dict[str, Any]] = {}
    if not RAW_ORIGINALS_DIR.exists():
        return found
    pattern = re.compile(r"^([A-Za-z0-9_-]+)_\d{4}-\d{2}_")
    for path in RAW_ORIGINALS_DIR.glob("*"):
        if path.suffix.lower() not in (".csv", ".json", ".meta.json"):
            continue
        match = pattern.match(path.name)
        if match:
            _add_found(found, match.group(1))
    return found


def _derive_from_evidence() -> dict[str, dict[str, Any]]:
    """Extrai propriedades dos pacotes de evidência persistidos."""
    found: dict[str, dict[str, Any]] = {}
    if not EVIDENCE_PACKAGES_DIR.exists():
        return found
    for path in EVIDENCE_PACKAGES_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        pid = data.get("property_id")
        if not pid:
            continue
        canonical = LEGACY_ALIASES.get(pid, pid)
        if canonical not in found:
            found[canonical] = _entry(canonical, data.get("property_name"))
    return found


def load_property_catalog() -> list[dict[str, Any]]:
    """Catálogo: dados persistidos; fixtures demo só com USE_MOCK_DATA."""
    catalog: dict[str, dict[str, Any]] = {}
    if config.USE_MOCK_DATA:
        catalog = {p["property_id"]: dict(p) for p in MOCK_PROPERTIES}

    for source in (_derive_from_cycles(), _derive_from_evidence(), _derive_from_raw_originals()):
        for pid, entry in source.items():
            if pid not in catalog:
                catalog[pid] = entry
            elif not catalog[pid].get("name") or catalog[pid]["name"] == pid:
                catalog[pid]["name"] = entry.get("name") or catalog[pid]["name"]

    return sorted(catalog.values(), key=lambda p: p.get("name") or p["property_id"])


def get_property(property_id: str, catalog: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Retorna a entrada de catálogo para um ID (resolvendo aliases)."""
    canonical = LEGACY_ALIASES.get(property_id, property_id)
    catalog = catalog if catalog is not None else load_property_catalog()
    for p in catalog:
        if p["property_id"] == canonical:
            return p
    return None
