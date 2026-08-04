"""Persistência de arquivos brutos e ciclos no protótipo."""

from __future__ import annotations

import copy
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from config import CYCLES_DIR, ensure_data_dirs
from utils.date_helpers import now_iso

logger = logging.getLogger("agrotrace.store")

# ── Cache em memória (invalidação por mtime do diretório / arquivo) ───────────
_cycles_list_cache: list[dict[str, Any]] | None = None
_cycles_list_signature: tuple[int, float] | None = None
_cycle_file_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cycles_dir_signature() -> tuple[int, float]:
    ensure_data_dirs()
    files = list(CYCLES_DIR.glob("*.json"))
    if not files:
        return (0, 0.0)
    return (len(files), max(f.stat().st_mtime for f in files))


def invalidate_cycle_cache(cycle_id: str | None = None) -> None:
    """Invalida cache de listagem e/ou de um ciclo específico."""
    global _cycles_list_cache, _cycles_list_signature
    _cycles_list_cache = None
    _cycles_list_signature = None
    if cycle_id:
        _cycle_file_cache.pop(cycle_id, None)
    else:
        _cycle_file_cache.clear()
    try:
        from services.property_registry import invalidate_property_catalog_cache

        invalidate_property_catalog_cache()
    except Exception:
        pass
    logger.debug("[STORE] invalidate_cycle_cache cycle_id=%s", cycle_id)


def _cycle_to_summary(cycle: dict[str, Any]) -> dict[str, Any]:
    calc = cycle.get("calculation") or {}
    approval = cycle.get("approval") or {}
    steps = cycle.get("steps") or {}
    pub = steps.get("publication") or {}
    return {
        "cycle_id": cycle.get("cycle_id"),
        "property_id": cycle.get("property_id"),
        "property_name": cycle.get("property_name"),
        "reporting_period": cycle.get("reporting_period"),
        "granularity": cycle.get("granularity"),
        "current_status": cycle.get("current_status") or cycle.get("status"),
        "status": cycle.get("status"),
        "updated_at": cycle.get("updated_at"),
        "created_at": cycle.get("created_at"),
        "approval_decision": approval.get("decision"),
        "publication_status": pub.get("status"),
        "co2e_total_kg": calc.get("co2e_total_kg"),
        "has_calculation": bool(calc),
        "has_normalized": bool((cycle.get("wrapper") or {}).get("normalized_payload")),
    }


def save_raw_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Preserva o arquivo original via serviço save-file e retorna metadados.

    A gravação do dado bruto é responsabilidade do serviço
    ``agrotrace-carbon-save-file`` (consumido por ``save_file_adapter``); esta
    função é mantida como fachada estável para os chamadores existentes.
    """
    from services.save_file_adapter import save_raw_file as _save

    return _save(
        source_path,
        property_id=property_id,
        reporting_period=reporting_period,
        original_filename=original_filename,
    )


def save_uploaded_content(
    content: bytes | str,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str,
) -> dict[str, Any]:
    """Preserva conteúdo enviado via upload do Dash através do serviço save-file."""
    from services.save_file_adapter import save_uploaded_content as _save

    return _save(
        content,
        property_id=property_id,
        reporting_period=reporting_period,
        original_filename=original_filename,
    )


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Salva dict como JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    """Carrega JSON ou retorna dict vazio."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def list_cycles() -> list[dict[str, Any]]:
    """Lista todos os ciclos salvos (com cache invalidado por mtime do diretório)."""
    global _cycles_list_cache, _cycles_list_signature

    sig = _cycles_dir_signature()
    if _cycles_list_cache is not None and _cycles_list_signature == sig:
        return copy.deepcopy(_cycles_list_cache)

    ensure_data_dirs()
    cycles: list[dict[str, Any]] = []
    for f in sorted(CYCLES_DIR.glob("*.json"), reverse=True):
        try:
            cycles.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue

    _cycles_list_cache = cycles
    _cycles_list_signature = sig
    logger.debug("[STORE] list_cycles count=%d (cache miss)", len(cycles))
    return copy.deepcopy(cycles)


def list_cycle_summaries() -> list[dict[str, Any]]:
    """Índice leve dos ciclos para tabelas, filtros e dropdowns."""
    return [_cycle_to_summary(c) for c in list_cycles()]


def save_cycle(cycle: dict[str, Any]) -> str:
    """Persiste ciclo e retorna cycle_id."""
    ensure_data_dirs()
    cycle_id = cycle.get("cycle_id") or f"CYCLE-{uuid.uuid4().hex[:12]}"
    cycle["cycle_id"] = cycle_id
    cycle["updated_at"] = now_iso()
    path = CYCLES_DIR / f"{cycle_id}.json"
    serializable = {k: v for k, v in cycle.items() if not k.startswith("_")}
    save_json(path, serializable)
    invalidate_cycle_cache(cycle_id)
    logger.info(
        "[STORE] save_cycle id=%s property=%s period=%s status=%s",
        cycle_id,
        cycle.get("property_id"),
        cycle.get("reporting_period"),
        cycle.get("current_status"),
    )
    return cycle_id


def get_cycle(cycle_id: str) -> dict[str, Any] | None:
    """Carrega ciclo por ID (cache por mtime do arquivo)."""
    path = CYCLES_DIR / f"{cycle_id}.json"
    if not path.exists():
        _cycle_file_cache.pop(cycle_id, None)
        return None

    mtime = path.stat().st_mtime
    cached = _cycle_file_cache.get(cycle_id)
    if cached and cached[0] == mtime:
        return copy.deepcopy(cached[1])

    data = load_json(path)
    _cycle_file_cache[cycle_id] = (mtime, data)
    return copy.deepcopy(data)


def get_active_cycle() -> dict[str, Any] | None:
    """Retorna o ciclo mais recente não verificado ou o mais recente."""
    cycles = list_cycles()
    if not cycles:
        return None
    for c in cycles:
        ver_status = (c.get("steps") or {}).get("verification", {}).get("status")
        if ver_status not in ("VERIFIED", "DIVERGENT") and c.get("status") not in ("VERIFIED", "VERIFICATION_FAILED"):
            return c
    return cycles[0]
