"""Tabela de comparação de integridade."""

from __future__ import annotations

from dash import html

from components.status_badges import StatusBadge
from components.tables import IntegrityDataTable


def IntegrityComparisonTable(integrity: dict | None) -> html.Div:
    if not integrity:
        return html.Div("Execute a verificação de integridade.", className="empty-state")

    rows = integrity.get("rows", [])
    final = integrity.get("final_status", "—")
    is_valid = integrity.get("is_valid")
    if is_valid is True:
        alert_class = "integrity-alert-success"
    elif is_valid is False:
        alert_class = "integrity-alert-danger"
    else:
        alert_class = "integrity-alert-pending"

    return html.Div([
        html.Div(final, className=f"alert mb-3 {alert_class}", role="alert") if final and final != "—" else None,
        IntegrityDataTable(rows, columns=["artifact", "anchored_hash", "recalculated_hash", "status"])
        if rows else html.Div("Execute a verificação de integridade.", className="empty-state"),
        html.Div([
            html.Strong("Modo: "),
            StatusBadge(integrity.get("mode") or integrity.get("source") or "PENDING"),
            html.Span(integrity.get("message", ""), className="d-block mt-1 text-aux"),
        ], className="mt-3"),
    ])
