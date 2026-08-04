"""Accordion de subcálculos e fórmulas."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import SectionHeader
from components.emission_detail.scope import ScopeBadge
from utils.formatting import format_t_co2e


def EmissionFormulaAccordion(formulas: list[dict], *, cycle_id: str | None, period: str | None) -> html.Div:
    if not formulas:
        return html.Div(
            html.P("Subcálculos não disponíveis para este ciclo.", className="text-aux"),
            className="emission-detail-section mb-4",
        )

    items = []
    for i, f in enumerate(formulas):
        body = [
            html.P([html.Strong("Fórmula: "), f.get("formula", "—")], className="small"),
            html.P([html.Strong("Gás: "), f.get("gas", "—")], className="small"),
            html.P([html.Strong("Resultado: "), f"{f.get('result_kg')} {f.get('unit', '')}"], className="small"),
        ]
        if f.get("co2e_t") is not None:
            body.append(html.P([html.Strong("CO₂e: "), format_t_co2e(f["co2e_t"])], className="small"))
        body.append(html.P([html.Strong("Origem: "), f.get("data_source", "—")], className="small text-aux"))
        if f.get("inputs"):
            body.append(html.H6("Entradas", className="small mt-2"))
            body.append(html.Pre(str(f["inputs"])[:600], className="small bg-light p-2 rounded"))
        if f.get("factors"):
            body.append(html.H6("Fatores", className="small mt-2"))
            body.append(html.Pre(str(f["factors"])[:600], className="small bg-light p-2 rounded"))

        items.append(dbc.AccordionItem(
            body,
            title=f.get("label", f"Subcálculo {i + 1}"),
            item_id=f"emission-formula-{f.get('id', i)}",
        ))

    return html.Div([
        SectionHeader("Subcálculos e fórmulas", "Métodos, entradas e fatores por etapa"),
        ScopeBadge(consolidated=False, cycle_id=cycle_id, period=period),
        dbc.Accordion(items, start_collapsed=True, flush=True, className="emission-formula-accordion"),
    ], className="emission-detail-section mb-4")
