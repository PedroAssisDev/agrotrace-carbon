"""Matriz de conformidade da auditoria."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.tables import DataTable


_STATUS_VARIANT = {
    "OK": "success",
    "Pendente": "secondary",
    "Atenção": "warning",
    "Erro": "danger",
    "N/A": "light",
}


def AuditComplianceMatrix(matrix: list[dict]) -> html.Div:
    if not matrix:
        return html.Div("Nenhum item de conformidade.", className="empty-state")

    rows = [{
        "item": r.get("item"),
        "status": r.get("status"),
        "servico": r.get("service"),
        "observacao": r.get("note"),
    } for r in matrix]

    summary = {}
    for r in matrix:
        summary[r.get("status", "—")] = summary.get(r.get("status", "—"), 0) + 1

    chips = []
    for status, count in sorted(summary.items()):
        chips.append(html.Span(
            f"{status}: {count}",
            className=f"badge bg-{_STATUS_VARIANT.get(status, 'secondary')} me-1 mb-1",
        ))

    return html.Div([
        html.H5("Matriz de conformidade", className="section-title"),
        html.Div(chips, className="mb-3"),
        DataTable(rows, columns=["item", "status", "servico", "observacao"]),
    ], className="audit-compliance-matrix")
