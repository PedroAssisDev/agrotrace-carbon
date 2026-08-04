"""Cadastro local de fazendas — persistência JSON no protótipo."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import config
from utils.date_helpers import now_iso


class FarmRegistryError(ValueError):
    """Erro de validação ou persistência no cadastro de fazenda."""


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split()).casefold()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().upper())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:40] or "FARM"


def list_persisted_properties() -> list[dict[str, Any]]:
    """Lista fazendas persistidas em ``frontend/data/properties/*.json``."""
    config.ensure_data_dirs()
    out: list[dict[str, Any]] = []
    props_dir = config.PROPERTIES_DIR
    if not props_dir.exists():
        return out
    for path in sorted(props_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("property_id"):
            out.append(data)
    return out


def find_by_name(name: str, catalog: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Busca fazenda por nome (case-insensitive) no catálogo informado ou completo."""
    target = _normalize_name(name)
    if not target:
        return None
    if catalog is None:
        from services.property_registry import load_property_catalog

        catalog = load_property_catalog()
    for entry in catalog:
        if _normalize_name(entry.get("name") or "") == target:
            return entry
    return None


def save_property(entry: dict[str, Any]) -> dict[str, Any]:
    """Persiste uma entrada de fazenda em JSON."""
    config.ensure_data_dirs()
    property_id = entry.get("property_id")
    if not property_id:
        raise FarmRegistryError("property_id é obrigatório para salvar a fazenda.")
    path = config.PROPERTIES_DIR / f"{property_id}.json"
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


def register_farm(
    name: str,
    *,
    municipality: str = "",
    state: str = "",
    production_type: str | None = None,
) -> dict[str, Any]:
    """Cadastra fazenda nova ou reutiliza existente com o mesmo nome."""
    clean_name = " ".join((name or "").strip().split())
    if not clean_name:
        raise FarmRegistryError("Informe o nome da fazenda.")

    existing = find_by_name(clean_name)
    if existing:
        return existing

    property_id = f"FARM-{_slugify(clean_name)}-{uuid.uuid4().hex[:6].upper()}"
    entry = {
        "property_id": property_id,
        "name": clean_name,
        "municipality": (municipality or "").strip(),
        "state": (state or "").strip().upper()[:2],
        "production_type": production_type,
        "created_at": now_iso(),
    }
    return save_property(entry)


def resolve_or_register_farm(farm_name: str, **kwargs: Any) -> dict[str, Any]:
    """Resolve fazenda pelo nome; cadastra localmente se ainda não existir."""
    return register_farm(farm_name, **kwargs)
