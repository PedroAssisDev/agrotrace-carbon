"""Cache em memória do objeto Owlready2 por cycle_id (evita circular imports)."""

from __future__ import annotations

from typing import Any

_ONTOLOGY_CACHE: dict[str, Any] = {}


def get_ontology(cycle_id: str | None) -> Any | None:
    if not cycle_id:
        return None
    return _ONTOLOGY_CACHE.get(cycle_id)


def set_ontology(cycle_id: str, onto: Any) -> None:
    if cycle_id and onto is not None:
        _ONTOLOGY_CACHE[cycle_id] = onto


def pop_ontology(cycle_id: str | None) -> Any | None:
    if not cycle_id:
        return None
    return _ONTOLOGY_CACHE.pop(cycle_id, None)


def invalidate(cycle_id: str | None = None) -> None:
    if cycle_id:
        pop_ontology(cycle_id)
    else:
        clear()


def clear() -> None:
    _ONTOLOGY_CACHE.clear()
