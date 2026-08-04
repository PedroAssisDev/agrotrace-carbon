"""Cards principais de emissões."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import CompactMetricCard, KpiGrid


def EmissionOverviewCards(cards: list[dict]) -> dbc.Row:
    if not cards:
        return dbc.Row()
    return KpiGrid(cards, col_md=3)


def EmissionVariationCards(variation: dict) -> html.Div:
    if not variation.get("has_variation"):
        return html.Div(
            html.P(
                "Não há série temporal suficiente para calcular variação.",
                className="text-aux small mb-0",
            ),
            className="emission-empty-hint p-3",
        )

    cols = []
    for item in variation.get("items") or []:
        pct = item.get("variation_pct")
        val = f"{pct}%" if pct not in (None, "não disponível", "—") else "—"
        color = "success" if isinstance(pct, (int, float)) and pct < 0 else (
            "danger" if isinstance(pct, (int, float)) and pct > 0 else "secondary"
        )
        cols.append(dbc.Col(
            CompactMetricCard(
                item.get("metric", "—"),
                val,
                subtitle="do início ao fim do período",
                icon="fas fa-chart-line",
                color=color,
            ),
            md=3,
            className="mb-2",
        ))
    return html.Div(dbc.Row(cols, className="g-2 emission-variation-grid"), className="emission-variation-section")
