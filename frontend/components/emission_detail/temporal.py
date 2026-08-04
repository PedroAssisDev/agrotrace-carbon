"""Gráficos temporais de emissões."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import SectionHeader
from components.charts import (
    IntensityTrendChart,
    LineChart,
    MultiLineTemporalChart,
    TemporalLineChart,
    temporal_chart_empty_card,
)
from components.emission_detail.scope import ScopeBadge


def _temporal_line_chart(title: str, labels: list, values: list):
    return (
        TemporalLineChart(title, labels, values, yaxis_title="t CO₂e", min_points=1)
        or LineChart(title, labels, values, yaxis_title="t CO₂e")
    )


def EmissionTemporalSection(timeseries: dict) -> html.Div:
    labels = timeseries.get("labels") or []
    total_t = timeseries.get("total_t") or []
    intensity = timeseries.get("intensity") or []

    children: list = [
        SectionHeader("Evolução temporal das emissões", "Total consolidado do período filtrado"),
        ScopeBadge(consolidated=True),
    ]

    if not timeseries.get("has_series"):
        children.append(temporal_chart_empty_card("Não há cálculo com série temporal para o período filtrado."))
        return html.Div(children, className="emission-detail-section mb-4")

    total_chart = _temporal_line_chart(
        "Emissões totais — evolução (t CO₂e)",
        labels,
        total_t,
    )

    children.append(dbc.Row([dbc.Col(total_chart, md=12, className="mb-3")], className="g-2"))

    by_gas = timeseries.get("by_gas") or {}
    multi_gas = MultiLineTemporalChart(
        "Comparativo de gases (t CO₂e)",
        labels,
        by_gas,
        yaxis_title="t CO₂e",
        min_points=1,
    )
    if multi_gas:
        children.append(html.Div([
            SectionHeader("Comparativo por gás", "CH₄, N₂O e CO₂"),
            dbc.Row([dbc.Col(multi_gas, md=12, className="mb-3")], className="g-2"),
        ], className="mt-2"))

    if intensity and labels:
        int_chart = IntensityTrendChart(labels, intensity)
        children.append(dbc.Row([dbc.Col(int_chart, md=12, className="mb-3 mt-2")], className="g-2"))

    return html.Div(children, className="emission-detail-section mb-4")
