"""Seletor de arquivo/ciclo para revisão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.tables import DataTable
from services.calculation_review_service import build_file_select_rows


def FileReviewSelector(cycles: list[dict], selected_cycle_id: str | None = None) -> html.Div:
    rows = build_file_select_rows(cycles)
    if not rows:
        return html.Div()

    return html.Div([
        html.H6("Arquivos para revisão", className="card-title mb-3"),
        html.Div(
            DataTable(
                rows,
                columns=["arquivo", "fazenda", "periodo", "pipeline_status", "review_status", "pendentes"],
            ),
            className="table-responsive cr-file-table",
        ),
        html.Small("Selecionar ciclo:", className="text-aux d-block mt-3"),
        dbc.Select(
            id="approval-cycle-select",
            options=[{"label": f"{r['arquivo']} — {r['periodo']}", "value": r["cycle_id"]} for r in rows],
            value=selected_cycle_id or (rows[0]["cycle_id"] if rows else None),
            size="sm",
            className="form-select-narrow mt-1",
        ),
    ], className="cr-file-selector")
