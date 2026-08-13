"""Defaults temporais unificados para toda a orquestração."""

from __future__ import annotations

from emissions.temporal_scope import TemporalScope


def default_days_in_period(temporal_scope: TemporalScope) -> int:
    """
    Comprimento padrão do período alinhado ao escopo temporal.

    - annual: 365 dias (ano civil típico)
    - monthly: 30 dias (mês comercial padrão)
    """
    return 365 if temporal_scope is TemporalScope.ANNUAL else 30


def resolve_days_in_period(
    temporal_scope: TemporalScope,
    days_in_period: int | None = None,
) -> int:
    """Retorna ``days_in_period`` explícito ou o default do escopo."""
    if days_in_period is None:
        return default_days_in_period(temporal_scope)
    return days_in_period
