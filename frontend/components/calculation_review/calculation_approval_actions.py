"""Ações de aprovação por item — UI enxuta, fluxo completo."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from services.result_correction_service import correctable_fields_for_item


def _needs_zero_confirmation(item: dict) -> bool:
    st = item.get("status", "AWAITING_REVIEW")
    if st not in ("COM_ZERO_ASSUMIDO", "AWAITING_REVIEW"):
        return False
    zeros = item.get("zero_assumptions") or []
    return any(not z.get("confirmed") for z in zeros)


def CalculationApprovalActions(item: dict | None, cycle: dict | None = None) -> html.Div:
    if not item:
        return html.Div()

    needs_zero = _needs_zero_confirmation(item)
    fields = (
        correctable_fields_for_item(
            cycle or {},
            item.get("calculation_item_id"),
            item.get("formula_id"),
        )
        if cycle
        else []
    )
    field_options = [
        {"label": f.get("label") or f.get("field"), "value": f.get("field")}
        for f in fields
    ]

    approve_label = "Aprovar (confirma zeros)" if needs_zero else "Aprovar"
    parts: list = [
        html.Div([
            dbc.Button(
                approve_label,
                id="cr-btn-approve-item",
                color="success",
                size="sm",
                className="me-1",
            ),
            dbc.Button(
                "Rejeitar",
                id="cr-btn-reject-item",
                color="danger",
                size="sm",
                outline=True,
                className="me-1",
            ),
            dbc.Button(
                "Solicitar correção",
                id="cr-btn-request-correction",
                color="secondary",
                size="sm",
                outline=True,
            ),
            # Mantido oculto para compatibilidade de layout/callbacks legados
            html.Div(
                dbc.Button(id="cr-btn-approve-zero", n_clicks=0),
                style={"display": "none"},
            ),
        ], className="d-flex flex-wrap gap-1 align-items-center"),
    ]

    if needs_zero:
        parts.append(html.Small(
            "Este cálculo tem zeros assumidos — Aprovar confirma a ausência de dado.",
            className="text-aux d-block mt-2",
        ))

    if field_options:
        parts.append(html.Div([
            html.Label("Campos para correção", className="small text-muted mb-1"),
            dcc.Dropdown(
                id="cr-correctable-fields",
                options=field_options,
                multi=True,
                placeholder="Opcional ao solicitar correção…",
                className="mb-0",
            ),
        ], className="mt-2"))
    else:
        parts.append(
            html.Div(dcc.Dropdown(id="cr-correctable-fields", options=[], style={"display": "none"}))
        )

    parts.append(html.Div(id="cr-item-action-feedback", className="small mt-2"))

    return html.Div(parts, className="cr-approval-actions")
