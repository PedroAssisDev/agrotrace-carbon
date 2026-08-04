"""Campos únicos de revisor/justificativa — compartilhados por item e finalização."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def ApprovalReviewerFields() -> html.Div:
    return html.Div([
        html.H6("Revisor", className="small mb-2"),
        dbc.Input(id="cr-reviewer", placeholder="Nome do revisor", size="sm", className="mb-2", value="Revisor"),
        dbc.Textarea(
            id="cr-justification",
            placeholder="Justificativa (obrigatória para rejeição/correção)",
            rows=2,
            className="small mb-0",
        ),
    ], className="cr-reviewer-fields")
