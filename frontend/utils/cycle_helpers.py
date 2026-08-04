"""Helpers para serialização de ciclos em dcc.Store."""

from __future__ import annotations


def strip_private_keys(cycle: dict) -> dict:
    """Remove chaves internas (prefixo _) antes de persistir no Store."""
    return {k: v for k, v in cycle.items() if not k.startswith("_")}
