"""Seletor de arquivo — usado dentro da toolbar de revisão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from services.calculation_review_service import build_file_select_rows


def FileReviewSelector(cycles: list[dict], selected_cycle_id: str | None = None) -> html.Div:
    """Dropdown de arquivo (sem meta agregada enganosa)."""
    rows = build_file_select_rows(cycles)
    if not rows:
        return html.Div()

    options = [
        {
            "label": f"{r['arquivo']} — {r['periodo']}",
            "value": r["cycle_id"],
        }
        for r in rows
    ]
    selected = selected_cycle_id or (rows[0]["cycle_id"] if rows else None)

    return html.Div([
        html.Label("Arquivo em revisão", className="small text-aux mb-1 d-block"),
        dbc.Select(
            id="approval-cycle-select",
            options=options,
            value=selected,
            size="sm",
            className="form-select-narrow",
        ),
    ], className="cr-file-selector")
