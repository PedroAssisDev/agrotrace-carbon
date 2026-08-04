"""Card de resumo de cálculo preliminar ou oficial."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import CompactMetricCard
from components.managerial_status import ApprovalStatusBadge
from services.cycle_status_service import resolve_managerial_status
from services.calculation_view_service import build_preliminary_result, build_source_breakdown
from utils.formatting import format_co2e, format_intensity, format_number


def CalculationSummaryCard(cycle: dict, *, show_sources: bool = False) -> dbc.Card:
    prelim = build_preliminary_result(cycle)
    st = resolve_managerial_status(cycle)
    body: list = [
        html.Div([ApprovalStatusBadge(st)], className="mb-3"),
        dbc.Row([
            dbc.Col(
                CompactMetricCard(
                    "Total CO₂e",
                    format_co2e(prelim.get("co2e_total_kg")),
                    icon="fas fa-cloud",
                    color="success",
                ),
                md=4,
            ),
            dbc.Col(
                CompactMetricCard(
                    "Intensidade",
                    format_intensity(prelim.get("intensity")),
                    icon="fas fa-tint",
                    color="primary",
                ),
                md=4,
            ),
            dbc.Col(
                CompactMetricCard(
                    "Produção leite",
                    format_number(prelim.get("milk_production")),
                    icon="fas fa-glass-whiskey",
                    color="info",
                ),
                md=4,
            ),
        ], className="g-2 mb-2"),
    ]
    if show_sources:
        sources = build_source_breakdown(cycle)
        if sources:
            body.append(html.H6("Principais fontes", className="card-title mt-2"))
            body.append(html.Ul(
                [html.Li(f"{s['fonte']}: {format_co2e(s['co2e_kg'])}") for s in sources[:6]],
                className="text-aux mb-0",
            ))
    return dbc.Card(dbc.CardBody(body), className="agro-card status-card mb-3")
