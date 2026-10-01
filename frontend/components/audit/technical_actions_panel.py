"""Painel técnico — referência expandida por padrão (RF020 / RNF007)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def TechnicalActionsPanel() -> html.Div:
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
