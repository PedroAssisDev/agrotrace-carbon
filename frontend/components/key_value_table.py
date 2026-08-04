"""Tabela chave-valor reutilizável."""

from __future__ import annotations

from dash import html


def KeyValueTable(data: dict, *, className: str = "table table-sm agro-table") -> html.Table:
    rows = [html.Tr([html.Th(str(k)), html.Td(str(v or "—"))]) for k, v in (data or {}).items()]
    return html.Table(html.Tbody(rows), className=className)
