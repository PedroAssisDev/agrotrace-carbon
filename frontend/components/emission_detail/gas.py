"""Quebra por gás."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import SectionHeader
from components.emission_detail.scope import ScopeBadge
from utils.formatting import format_percent, format_t_co2e


def EmissionGasBreakdown(gas_data: dict) -> html.Div:
    rows = gas_data.get("rows") or []
    if not rows:
        return html.Div(
            html.P("Não há dados por gás.", className="text-aux"),
            className="emission-detail-section mb-4",
        )

    cards = []
    for r in rows:
        pct = r.get("participacao_pct")
        cards.append(dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6(r["gas"], className="card-title"),
                html.Strong(format_t_co2e(r.get("co2e_t")), className="metric-value d-block"),
                html.Small(format_percent(pct) + " do total" if pct is not None else "", className="text-aux"),
            ]), className="metric-card h-100"),
            md=4,
            className="mb-2",
        ))

    return html.Div([
        SectionHeader("Emissões por gás", "Participação e fontes relacionadas (t CO₂e)"),
        ScopeBadge(consolidated=True),
        dbc.Row(cards, className="g-2 mb-3"),
    ], className="emission-detail-section mb-4")
