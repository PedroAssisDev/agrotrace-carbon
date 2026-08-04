"""Helpers para serialização de ciclos em dcc.Store."""

from __future__ import annotations

from typing import Any

from utils.file_helpers import get_cycle


def strip_private_keys(cycle: dict) -> dict:
    """Remove chaves internas (prefixo _) antes de persistir no Store."""
    return {k: v for k, v in cycle.items() if not k.startswith("_")}


def cycle_store_summary(cycle: dict[str, Any] | None) -> dict[str, Any]:
    """Payload leve para dcc.Store — detalhe completo via get_cycle(cycle_id)."""
    if not cycle or not cycle.get("cycle_id"):
        return {}
    calc = cycle.get("calculation") or {}
    approval = cycle.get("approval") or {}
    steps = cycle.get("steps") or {}
    pub = steps.get("publication") or {}
    raw = cycle.get("raw_file") or {}
    return {
        "cycle_id": cycle.get("cycle_id"),
        "property_id": cycle.get("property_id"),
        "property_name": cycle.get("property_name"),
        "reporting_period": cycle.get("reporting_period"),
        "granularity": cycle.get("granularity"),
        "current_status": cycle.get("current_status") or cycle.get("status"),
        "status": cycle.get("status"),
        "updated_at": cycle.get("updated_at"),
        "approval_decision": approval.get("decision"),
        "publication_status": pub.get("status"),
        "co2e_total_kg": calc.get("co2e_total_kg"),
        "original_filename": raw.get("original_filename"),
        "_store_mode": "summary",
    }


def ensure_full_cycle(cycle: dict[str, Any] | None) -> dict[str, Any]:
    """Garante ciclo completo — carrega do disco se o store tiver apenas resumo."""
    if not cycle or not cycle.get("cycle_id"):
        return {}
    if cycle.get("_store_mode") != "summary" and cycle.get("calculation") is not None:
        return strip_private_keys(cycle)
    loaded = get_cycle(cycle["cycle_id"])
    return strip_private_keys(loaded) if loaded else {}
