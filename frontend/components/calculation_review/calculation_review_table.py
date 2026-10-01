"""Tabela de cálculos revisáveis."""

from __future__ import annotations

from dash import dash_table, html

from layout.theme import COLORS
from services.calculation_review_service import build_review_table_rows

_STATUS_LABELS = {
    "AWAITING_REVIEW": "Aguardando",
    "COM_ZERO_ASSUMIDO": "Zero assumido",
    "APPROVED": "Aprovado",
    "APPROVED_WITH_ZERO": "Aprovado c/ zero",
    "APPROVED_WITH_MANUAL_ADJUSTMENT": "Aprovado c/ ajuste",
    "REJECTED": "Rejeitado",
    "CORRECTION_REQUESTED": "Correção",
    "ADJUSTMENT_PENDING_RECALCULATION": "Recálculo pendente",
    "NOT_APPLICABLE": "N/A",
}


def CalculationReviewTable(cycle: dict, selected_item_id: str | None = None) -> html.Div:
    rows = build_review_table_rows(cycle)
    table_rows = []
    selected_index = 0
    for idx, r in enumerate(rows):
        item_id = r["calculation_item_id"]
        if selected_item_id and item_id == selected_item_id:
            selected_index = idx
        table_rows.append({
            "calculation_item_id": item_id,
            "formula_id": r.get("formula_id"),
            "calculo": r["calculo"],
            "resultado": r["resultado"],
            "unidade": r["unidade"],
            "co2e_kg": r["co2e_kg"],
            "status": _STATUS_LABELS.get(r["status"], r["status"]),
        })

    parts = [
        html.H6("Cálculos do arquivo", className="card-title mb-2"),
        html.P("Selecione uma linha para revisar.", className="small text-aux mb-2"),
    ]
    if not table_rows:
        parts.append(html.P("Nenhum cálculo disponível para revisão.", className="text-muted small mb-2"))

    parts.append(html.Div(
        dash_table.DataTable(
            id="cr-items-table",
            columns=[
                {"name": "Cálculo", "id": "calculo"},
                {"name": "Resultado", "id": "resultado"},
                {"name": "Unidade", "id": "unidade"},
                {"name": "CO₂e (kg)", "id": "co2e_kg"},
                {"name": "Status", "id": "status"},
            ],
            data=table_rows,
            hidden_columns=["calculation_item_id", "formula_id"],
            row_selectable="single",
            selected_rows=[selected_index] if table_rows else [],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={
                "fontSize": "0.875rem",
                "padding": "10px 12px",
                "textAlign": "left",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "64px",
                "maxWidth": "240px",
            },
            style_header={
                "fontWeight": "600",
                "fontSize": "0.8rem",
                "backgroundColor": COLORS.get("table_header", COLORS["surface_muted"]),
                "color": COLORS["text"],
                "borderBottom": f"1px solid {COLORS['border']}",
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "resultado"},
                    "textAlign": "right",
                    "fontVariantNumeric": "tabular-nums",
                },
                {
                    "if": {"column_id": "co2e_kg"},
                    "textAlign": "right",
                    "fontVariantNumeric": "tabular-nums",
                },
            ],
            css=[{
                "selector": ".dash-spreadsheet tr.row-selected td",
                "rule": f"background-color: {COLORS['status_success_bg']} !important; color: {COLORS['text']} !important;",
            }],
        ),
        className="cr-review-table",
    ))

    return html.Div(parts, className="cr-table-wrap")
