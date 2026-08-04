"""Painel de logs e alertas da auditoria."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.tables import DataTable


def _summary_card(title: str, count: int, variant: str) -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.H6(title, className="card-title small text-muted mb-1"),
        html.H4(str(count), className="mb-0"),
    ], className="py-2"), className=f"agro-card border-{variant}"), md=4, lg=2, className="mb-2")


def AuditLogPanel(log_data: dict) -> html.Div:
    summary = log_data.get("summary") or {}
    rows = log_data.get("rows") or []

    cards = dbc.Row([
        _summary_card("Erros críticos", summary.get("errors", 0), "danger"),
        _summary_card("Alertas", summary.get("warnings", 0), "warning"),
        _summary_card("Fallback mock", summary.get("mock_fallbacks", 0), "secondary"),
        _summary_card("Sem match ciclo", summary.get("no_match", 0), "info"),
        _summary_card("Eventos", summary.get("events", 0), "primary"),
    ], className="mb-3 g-2")

    sections = []
    for section_key, section_rows in (log_data.get("sections") or {}).items():
        if not section_rows:
            continue
        labels = {
            "cycle_errors": "Erros do ciclo",
            "cycle_warnings": "Alertas do ciclo",
            "provenance_events": "Eventos de proveniência",
            "adapter_failures": "Falhas de adapter / fallback",
            "filter_inconsistencies": "Inconsistências de filtro",
        }
        sections.append(html.Div([
            html.H6(labels.get(section_key, section_key), className="section-subtitle mt-3 mb-2"),
            DataTable(section_rows, columns=["severidade", "origem", "mensagem", "etapa", "timestamp", "detalhe"]),
        ]))

    return html.Div([
        html.H5("Logs e alertas", className="section-title mb-3"),
        cards,
        html.Div(sections) if sections else DataTable(
            rows,
            columns=["severidade", "origem", "mensagem", "etapa", "timestamp", "detalhe"],
        ) if rows else html.P("Nenhum log registrado.", className="text-muted"),
    ], className="audit-log-panel")
