"""Catálogo de propriedades do frontend.

Combina propriedades persistidas com propriedades derivadas dos ciclos já
salvos. O caminho quente da UI (filtro/navbar) NÃO varre ontologia OWL —
use ``load_property_catalog_from_ontology`` apenas quando a tela precisar
de dados semânticos.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

import config
from config import EVIDENCE_PACKAGES_DIR, RAW_ORIGINALS_DIR, SAVE_FILE_ORIGINALS_DIR
from utils.file_helpers import list_cycles
from utils.property_filter import get_all_property_ids

logger = logging.getLogger("agrotrace.property_registry")

# Cache do catálogo rápido (UI/filtro). Invalidado com ciclos / cadastro de fazenda.
_catalog_cache: list[dict[str, Any]] | None = None

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


def invalidate_property_catalog_cache() -> None:
    """Invalida cache do catálogo rápido (chamar ao salvar ciclo/fazenda)."""
    global _catalog_cache
    _catalog_cache = None
    logger.debug("[PROP] catalog cache invalidated")


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


def _derive_from_cycles(cycles: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Extrai propriedades únicas dos ciclos salvos (topo + campos aninhados)."""
    found: dict[str, dict[str, Any]] = {}
    for c in cycles if cycles is not None else list_cycles():
        for pid in get_all_property_ids(c):
            _add_found(found, pid, c.get("property_name"))
    return found


def _derive_from_raw_originals() -> dict[str, dict[str, Any]]:
    """Extrai property_id dos nomes de arquivo dos originais (save-file + legado)."""
    found: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"^([A-Za-z0-9_-]+)_\d{4}-\d{2}_")
    for originals_dir in (SAVE_FILE_ORIGINALS_DIR, RAW_ORIGINALS_DIR):
        if not originals_dir.exists():
            continue
        for path in originals_dir.glob("*"):
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


def _load_persisted_properties() -> dict[str, dict[str, Any]]:
    """Fazendas cadastradas explicitamente (prioridade sobre derivadas)."""
    try:
        from services.farm_registry_service import list_persisted_properties

        return {p["property_id"]: dict(p) for p in list_persisted_properties()}
    except Exception as exc:
        logger.warning("Falha ao carregar propriedades persistidas: %s", exc)
        return {}


def _build_fast_catalog(cycles: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Catálogo para UI/filtro: persistido + ciclos (+ mock). Sem OWL."""
    catalog: dict[str, dict[str, Any]] = _load_persisted_properties()

    for pid, entry in _derive_from_cycles(cycles).items():
        if pid not in catalog:
            entry = dict(entry)
            entry["source"] = "cycle_bootstrap"
            catalog[pid] = entry
        elif entry.get("name") and (
            not catalog[pid].get("name") or catalog[pid]["name"] == pid
        ):
            catalog[pid]["name"] = entry["name"]

    if config.USE_MOCK_DATA:
        for p in MOCK_PROPERTIES:
            if p["property_id"] not in catalog:
                catalog[p["property_id"]] = {**dict(p), "source": "mock"}

    return sorted(catalog.values(), key=lambda p: p.get("name") or p["property_id"])


def load_property_catalog() -> list[dict[str, Any]]:
    """Catálogo rápido para filtro/navbar (sem varredura de ontologia)."""
    global _catalog_cache
    if _catalog_cache is not None:
        return copy.deepcopy(_catalog_cache)
    built = _build_fast_catalog()
    _catalog_cache = built
    logger.debug("[PROP] catalog built entries=%d", len(built))
    return copy.deepcopy(built)


def load_property_catalog_from_ontology() -> list[dict[str, Any]]:
    """Catálogo enriquecido via OWL — uso pontual (telas/scripts semânticos)."""
    catalog: dict[str, dict[str, Any]] = {
        p["property_id"]: dict(p) for p in load_property_catalog()
    }

    try:
        from services.ontology_query_adapter import list_properties_from_ontology

        for p in list_properties_from_ontology():
            pid = p["property_id"]
            if pid not in catalog:
                catalog[pid] = {
                    "property_id": pid,
                    "name": p.get("name") or pid,
                    "municipality": p.get("municipality") or "",
                    "state": p.get("state") or "",
                    "source": "ontology",
                    "ontology_path": p.get("ontology_path"),
                    "ontology_version": p.get("ontology_version"),
                }
            else:
                catalog[pid]["source"] = catalog[pid].get("source") or "ontology"
                if p.get("name") and (
                    not catalog[pid].get("name") or catalog[pid]["name"] == pid
                ):
                    catalog[pid]["name"] = p["name"]
    except Exception as exc:
        logger.warning("Falha ao listar propriedades da ontologia: %s", exc)

    return sorted(catalog.values(), key=lambda p: p.get("name") or p["property_id"])


def get_property(property_id: str, catalog: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Retorna a entrada de catálogo para um ID (resolvendo aliases)."""
    canonical = LEGACY_ALIASES.get(property_id, property_id)
    catalog = catalog if catalog is not None else load_property_catalog()
    for p in catalog:
        if p["property_id"] == canonical:
            return p
    return None


def resolve_farm_name(
    farm_id: str | None,
    *,
    cycles: list[dict[str, Any]] | None = None,
    known_name: str | None = None,
) -> str | None:
    """Resolve nome da fazenda sem carregar catálogo OWL completo."""
    if not farm_id:
        return None
    if known_name and str(known_name).strip():
        return str(known_name).strip()

    canonical = LEGACY_ALIASES.get(farm_id, farm_id)
    for c in cycles if cycles is not None else list_cycles():
        if c.get("property_id") == canonical and c.get("property_name"):
            return c["property_name"]

    try:
        from services.farm_registry_service import list_persisted_properties

        for p in list_persisted_properties():
            if p.get("property_id") == canonical:
                return p.get("name") or farm_id
    except Exception:
        pass

    if _catalog_cache is not None:
        for p in _catalog_cache:
            if p.get("property_id") == canonical:
                return p.get("name") or farm_id

    return farm_id
