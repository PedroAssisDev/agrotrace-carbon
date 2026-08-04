"""Tabelas de fatores e parâmetros."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, SectionHeader
from components.emission_detail.scope import ScopeBadge
from components.tables import DataTable


def EmissionFactorsTable(factor_view: dict, *, cycle_id: str | None, period: str | None) -> html.Div:
    blocks = factor_view.get("blocks") or []
    if not blocks and factor_view.get("legacy_schema"):
        return html.Div([
            SectionHeader("Fatores e parâmetros"),
            ScopeBadge(consolidated=False, cycle_id=cycle_id, period=period),
            AlertBox(
                "Fatores detalhados não disponíveis para este ciclo (schema legado). Consulte subcálculos.",
                variant="info",
                className="small",
            ),
        ], className="emission-detail-section mb-4")

    sections: list = [
        SectionHeader("Fatores e parâmetros", factor_view.get("methodology") or "IPCC / GEE agropecuário"),
        ScopeBadge(consolidated=False, cycle_id=cycle_id, period=period),
    ]

    if factor_view.get("method_code"):
        sections.append(html.P(
            f"Método {factor_view.get('method_code')} v{factor_view.get('method_version')} • "
            f"implementação {factor_view.get('calculation_version')}",
            className="text-aux small",
        ))

    for block in blocks:
        rows = []
        for r in block.get("rows") or []:
            rows.append({
                "parametro": r.get("parametro") or r.get("label"),
                "valor": r.get("valor"),
                "unidade": r.get("unidade", "—"),
                "origem": r.get("origem", "—"),
                "default": "Sim" if r.get("is_default") else "Não",
            })
        if not rows:
            continue
        sections.append(dbc.Card(dbc.CardBody([
            html.H6(block.get("title", "Fatores"), className="card-title"),
            DataTable(rows, columns=["parametro", "valor", "unidade", "origem", "default"]),
        ]), className="agro-card mb-3"))

    return html.Div(sections, className="emission-detail-section mb-4")
