"""Seletor de variável de entrada alternativa (ontologia)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from services.calculation_input_mapping_service import list_compatible_alternatives


def CalculationInputVariableSelector(cycle: dict, item: dict) -> html.Div:
    if not item:
        return html.Div()

    required = item.get("required_variables") or []
    if not required:
        return html.P("Este cálculo não possui variáveis de entrada mapeáveis.", className="small text-muted")

    blocks = []
    for req in required[:2]:
        ov = req.get("ontology_var") or req.get("variable", "—")
        oclass = req.get("ontology_class", "—")
        alts = list_compatible_alternatives(cycle, ov, req.get("expected_unit"))
        options = [
            {
                "label": f"{a.get('ontology_var', a.get('variable'))} = {a.get('value')} ({a.get('unit')}) [{a.get('ontology_class', '')}]",
                "value": a.get("ontology_var") or a.get("variable"),
            }
            for a in alts
        ]
        if not options:
            options = [{"label": "Nenhuma alternativa compatível", "value": ""}]

        blocks.append(html.Div([
            html.Small(
                f"Variável ontológica: {ov} ({req.get('expected_unit', '—')}) — classe {oclass}",
                className="text-aux d-block mb-1",
            ),
            dbc.Select(
                id={"type": "cr-var-select", "target": ov},
                options=options,
                size="sm",
                className="mb-2",
            ),
        ], className="mb-2"))

    return html.Div([
        html.H6("Trocar variável de entrada", className="small mb-2"),
        *blocks,
        dbc.Button("Aplicar troca e recalcular", id="cr-btn-apply-swap", color="outline-primary", size="sm", className="mt-1"),
    ], className="cr-var-selector")
