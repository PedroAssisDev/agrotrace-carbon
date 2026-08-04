"""Selo de escopo (agregado vs ciclo específico)."""

from __future__ import annotations

from dash import html


def ScopeBadge(*, consolidated: bool, cycle_id: str | None = None, period: str | None = None) -> html.Span:
    if consolidated:
        text = "Agregado do período filtrado"
        cls = "emission-scope-badge emission-scope-badge--consolidated"
    else:
        label = period or cycle_id or "—"
        text = f"Ciclo específico: {label}"
        cls = "emission-scope-badge emission-scope-badge--cycle"
    return html.Span(text, className=cls)
