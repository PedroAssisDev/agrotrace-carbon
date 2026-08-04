"""Tabelas de apoio da Análise Geral."""

from __future__ import annotations

from dash import html

from components.cards import SectionHeader
from components.tables import DataTable


def SupportTablesSection(tables: dict, *, keys: list[str]) -> html.Div | None:
    blocks: list = []
    titles = {
        "ranking_sources": "Ranking de fontes emissoras",
        "period_indicators": "Indicadores por período",
        "cycles_analyzed": "Ciclos analisados",
        "management_alerts": "Alertas e pendências",
        "traceability": "Rastreabilidade dos dados",
    }
    for key in keys:
        rows = tables.get(key) or []
        if not rows:
            continue
        cols = list(rows[0].keys()) if rows else []
        blocks.append(html.Div([
            html.Div(SectionHeader(titles.get(key, key)), className="mt-3"),
            html.Div(DataTable(rows, columns=cols), className="table-responsive"),
        ], className="support-table-block mb-3"))
    if not blocks:
        return None
    return html.Div(blocks, className="support-tables-section")
