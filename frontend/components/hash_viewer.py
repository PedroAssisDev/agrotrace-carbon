"""Visualizador de hashes."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from utils.hash_helpers import truncate_hash


def HashViewer(hashes: dict | None) -> html.Div:
    if not hashes:
        return html.Div("Nenhum hash registrado.", className="empty-state")
    rows = []
    for key, val in hashes.items():
        rows.append(html.Tr([
            html.Td(key),
            html.Td(truncate_hash(str(val), 16), className="hash-mono"),
            html.Td(str(val), className="hash-mono text-aux"),
        ]))
    return html.Div(
        dbc.Table([
            html.Thead(html.Tr([html.Th("Artefato"), html.Th("Resumo"), html.Th("Hash completo")])),
            html.Tbody(rows),
        ], bordered=False, hover=True, size="sm", className="mb-0"),
        className="agro-table mb-3",
    )
