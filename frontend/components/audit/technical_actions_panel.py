"""Painel técnico — referência expandida por padrão (RF020 / RNF007)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from config import SAMPLE_DATA_DIR


def TechnicalActionsPanel() -> html.Div:
    sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
    return html.Div([
        dbc.Accordion(
            [
                dbc.AccordionItem(
                    [
                        html.P(
                            "Ações técnicas principais: Entrada de Dados, Cálculos de Emissão "
                            "e Revisão e Aprovação. Cenários oficiais: scripts/seed_test_scenarios.py.",
                            className="text-aux small mb-2",
                        ),
                        html.Ul(
                            [
                                html.Li("Entrada de Dados — /data-entry", className="small"),
                                html.Li("Cálculos de Emissão — /calculations", className="small"),
                                html.Li("Revisão e Aprovação — /approval", className="small"),
                                html.Li("Auditoria Técnica — esta página (9 abas)", className="small"),
                            ],
                            className="mb-2 ps-3",
                        ),
                        html.Div(
                            [
                                dbc.Select(
                                    id="upload-sample",
                                    options=[{"label": f, "value": f} for f in sample_files],
                                    value=sample_files[0] if sample_files else None,
                                    style={"display": "none"},
                                ),
                                html.Button(id="btn-run-full-pipeline", n_clicks=0, style={"display": "none"}),
                                html.Button(id="btn-load-demo", n_clicks=0, style={"display": "none"}),
                            ],
                            id="ta-legacy-actions",
                        ),
                    ],
                    title="Ações técnicas",
                    item_id="ta-technical-actions-item",
                ),
            ],
            id="ta-technical-actions",
            start_collapsed=False,
            active_item="ta-technical-actions-item",
            className="audit-technical-actions mb-3",
        ),
    ])
