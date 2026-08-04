"""Tabela de artefatos do ciclo."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit.mock_source_badge import MockSourceBadge
from components.tables import DataTable


def AuditArtifactTable(
    grouped: dict[str, list[dict]],
    integration_mode: str | None = None,
) -> html.Div:
    if not grouped:
        return html.Div("Nenhum artefato registrado para este ciclo.", className="empty-state")

    sections = [
        html.Div([
            html.H5("Artefatos do ciclo", className="section-title d-inline-block me-2"),
            MockSourceBadge(integration_mode),
        ], className="mb-3"),
        html.P(
            "Artefatos preliminares não são apresentados como finais.",
            className="text-aux small mb-3",
        ),
    ]

    for group_key, rows in grouped.items():
        if not rows:
            continue
        label = rows[0].get("group_label", group_key)
        table_rows = [{
            "artefato": r.get("artifact"),
            "tipo": r.get("type"),
            "status": ("Preliminar — " if r.get("is_preliminary") else "") + r.get("status", "—"),
            "servico": r.get("service"),
            "origem": r.get("origin"),
            "hash": r.get("hash_short"),
            "gerado_em": r.get("generated_at"),
            "modo": r.get("mode"),
            "acao": r.get("action"),
        } for r in rows]
        sections.append(html.Div([
            html.H6(label, className="section-subtitle mt-3 mb-2"),
            DataTable(table_rows, columns=["artefato", "tipo", "status", "servico", "origem", "hash", "gerado_em", "modo", "acao"]),
        ]))

    return html.Div(sections, className="audit-artifact-table")
