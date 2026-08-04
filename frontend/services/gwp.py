"""Resolução de GWP a partir do calculation-service (fonte oficial)."""

from __future__ import annotations

from typing import Any


def resolve_gwp(explicit: dict[str, float] | None = None) -> dict[str, float]:
    """Retorna GWP explícito ou o default IPCC AR4 do calculation-service."""
    if explicit:
        return dict(explicit)
    from services import direct_imports as di

    if di.gwp_ipcc_ar4 is None:
        raise RuntimeError("emissions.defaults.gwp_ipcc_ar4 indisponível.")
    return dict(di.gwp_ipcc_ar4())
