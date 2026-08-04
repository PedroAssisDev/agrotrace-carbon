"""Ações de aprovação por item."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def CalculationApprovalActions(item: dict | None) -> html.Div:
    if not item:
        return html.Div()

    st = item.get("status", "AWAITING_REVIEW")
    has_zero = bool(item.get("zero_assumptions")) and st in ("COM_ZERO_ASSUMIDO", "AWAITING_REVIEW")

    return html.Div([
        html.H6("Ações do item", className="small mb-2"),
        dbc.ButtonGroup([
            dbc.Button("Aprovar", id="cr-btn-approve-item", color="success", size="sm", outline=True),
            dbc.Button("Aprovar c/ zero", id="cr-btn-approve-zero", color="warning", size="sm", outline=True, disabled=not has_zero),
            dbc.Button("Rejeitar", id="cr-btn-reject-item", color="danger", size="sm", outline=True),
            dbc.Button("Solicitar correção", id="cr-btn-request-correction", color="secondary", size="sm", outline=True),
        ], className="d-flex flex-wrap gap-1 mb-2"),
        html.Div(id="cr-item-action-feedback", className="small"),
    ], className="cr-approval-actions")
