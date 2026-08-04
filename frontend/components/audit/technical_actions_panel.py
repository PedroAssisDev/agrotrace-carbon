"""Painel colapsado de ações técnicas / demonstração."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from config import SAMPLE_DATA_DIR


def TechnicalActionsPanel() -> html.Div:
    sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
    return html.Div([
        dbc.Accordion([
            dbc.AccordionItem([
                dbc.Alert(
                    "Modo demonstração: pode usar dados simulados e aprovação automática. "
                    "Não use como fluxo operacional real.",
                    color="warning",
                    className="small py-2 mb-3",
                ),
                dbc.ButtonGroup([
                    dbc.Button(
                        "Pipeline completo (demo)",
                        id="btn-run-full-pipeline",
                        color="warning",
                        outline=True,
                        size="sm",
                        className="btn-agro-secondary",
                    ),
                    dbc.Button(
                        "Carregar demo",
                        id="btn-load-demo",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="btn-agro-secondary",
                    ),
                ]),
                html.Div([
                    dbc.Select(
                        id="upload-sample",
                        options=[{"label": f, "value": f} for f in sample_files],
                        value=sample_files[0] if sample_files else None,
                        style={"display": "none"},
                    ),
                ]),
                html.P(
                    "Execução operacional principal: Entrada de Dados, Cálculos de Emissão e Revisão e Aprovação.",
                    className="text-aux small mt-3 mb-0",
                ),
            ], title="Ações técnicas / Demonstração"),
        ], start_collapsed=True, className="audit-technical-actions mb-3"),
    ])
