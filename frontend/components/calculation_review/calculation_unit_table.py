"""Tabela de unidades do item."""

from __future__ import annotations

from dash import html

from components.tables import DataTable
from services.calculation_input_mapping_service import build_unit_rows


def CalculationUnitTable(item: dict) -> html.Div:
    if not item:
        return html.Div()
    rows = build_unit_rows(item)
    return html.Div([
        html.H6("Unidades", className="small mb-2"),
        DataTable(rows, columns=["variavel", "classe", "valor", "unidade_entrada", "unidade_esperada", "origem"]),
    ], className="cr-unit-table")
