"""Painel técnico — upload de amostra (sem demos com mock)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from config import SAMPLE_DATA_DIR


def TechnicalActionsPanel() -> html.Div:
    sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
    return html.Div([
        dbc.Accordion([
            dbc.AccordionItem([
                html.P(
                    "Ações operacionais principais: Entrada de Dados, Cálculos de Emissão e Revisão e Aprovação. "
                    "Cenários de teste oficiais: scripts/seed_test_scenarios.py.",
                    className="text-aux small mb-2",
                ),
                html.Div([
                    dbc.Select(
                        id="upload-sample",
                        options=[{"label": f, "value": f} for f in sample_files],
                        value=sample_files[0] if sample_files else None,
                        style={"display": "none"},
                    ),
                    # Placeholders ocultos para callbacks legacy não quebrarem (allow_optional)
                    html.Button(id="btn-run-full-pipeline", n_clicks=0, style={"display": "none"}),
                    html.Button(id="btn-load-demo", n_clicks=0, style={"display": "none"}),
                ]),
            ], title="Referência técnica"),
        ], start_collapsed=True, className="audit-technical-actions mb-3"),
    ])
