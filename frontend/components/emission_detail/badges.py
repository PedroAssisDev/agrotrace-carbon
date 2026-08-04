"""Badges do cabeçalho de Cálculos de Emissão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox


def EmissionCalcHeaderBadges(meta: dict) -> html.Div:
    badges: list = []
    if meta.get("is_preliminary"):
        badges.append(html.Span("Preliminar", className="badge-status badge-status-pendente me-1"))
    if meta.get("uses_mock"):
        badges.append(html.Span("Simulado", className="badge-status badge-status-mock me-1"))
    elif meta.get("uses_fallback"):
        badges.append(html.Span("Fallback", className="badge-status badge-status-warning me-1"))
    elif meta.get("mode") == "real":
        badges.append(html.Span("Dados reais", className="badge-status badge-status-dados-reais me-1"))
    if meta.get("has_tier2"):
        badges.append(html.Span("Tier 2", className="badge-status badge-status-info me-1"))

    alerts: list = []
    if meta.get("uses_fallback") or meta.get("uses_mock"):
        alerts.append(AlertBox(
            "Cálculo com dados simulados ou fallback em uma ou mais entradas.",
            variant="warning",
            className="small mb-0",
        ))

    if not badges and not alerts:
        return html.Div()

    return html.Div([
        html.Div(badges, className="d-flex flex-wrap gap-1 mb-2") if badges else None,
        *alerts,
    ], className="emission-header-badges mb-3")
