"""Timeline de auditoria (não operacional)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit.mock_source_badge import MockSourceBadge
from components.tables import DataTable


def AuditTimeline(timeline: list[dict], integration_mode: str | None = None) -> html.Div:
    if not timeline:
        return html.Div("Nenhuma etapa na linha do tempo.", className="empty-state")

    rows = [{
        "etapa": r.get("name"),
        "status": r.get("status"),
        "evento": r.get("event_type"),
        "servico": r.get("service"),
        "timestamp": r.get("timestamp"),
        "artefato": r.get("artifact"),
        "hash": r.get("hash_short"),
        "modo": r.get("mode"),
        "observacao": r.get("note"),
    } for r in timeline]

    return html.Div([
        html.Div([
            html.H5("Linha do tempo de auditoria", className="section-title d-inline-block me-2"),
            MockSourceBadge(integration_mode),
        ], className="mb-3"),
        html.P(
            "Timeline de verificação do ciclo de vida — não é um wizard de execução.",
            className="text-aux small mb-3",
        ),
        DataTable(rows, columns=["etapa", "status", "evento", "servico", "timestamp", "artefato", "hash", "modo", "observacao"]),
    ], className="audit-timeline")
