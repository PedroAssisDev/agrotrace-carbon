"""Visualizador de payload técnico."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.payload_viewer import PayloadViewer
from services.audit_payload_service import PAYLOAD_SOURCES


def AuditPayloadViewer(
    payload_result: dict | None = None,
    *,
    show_selector: bool = True,
    content_only: bool = False,
) -> html.Div:
    if content_only:
        if payload_result:
            data = payload_result.get("data")
            if data is not None:
                return html.Div([
                    html.H6(payload_result.get("title", "Payload"), className="section-subtitle mb-2"),
                    PayloadViewer(data, title=""),
                ])
            return html.P("Nenhum dado disponível para esta origem.", className="text-muted small")
        return html.P("Selecione a origem do payload.", className="text-muted small")

    options = [{"label": label, "value": key} for key, label in PAYLOAD_SOURCES]
    default_source = "cycle"

    body = []
    if show_selector:
        body.append(dbc.Row([
            dbc.Col(dbc.Select(
                id="ta-payload-source",
                options=options,
                value=default_source,
                size="sm",
            ), md=6),
        ], className="mb-3"))

    body.append(html.Div(id="ta-payload-content", children=AuditPayloadViewer(payload_result, content_only=True)))

    return html.Div([
        html.H5("Payload técnico", className="section-title"),
        html.P(
            "Visualização de JSONs técnicos para inspeção detalhada.",
            className="text-aux small mb-3",
        ),
        *body,
    ], className="audit-payload-viewer")
