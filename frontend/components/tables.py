"""Tabelas interativas."""

from __future__ import annotations

import json
from typing import Any

from dash import dash_table, html

from layout.theme import COLORS
from components.empty_state import EmptyState

_FONT = 'Inter, "Segoe UI", Roboto, Arial, sans-serif'
_ZEBRA_ROW = [{"if": {"row_index": "odd"}, "backgroundColor": COLORS.get("zebra", "#F8FAF8")}]

_TABLE_STYLE = {
    "style_table": {"overflowX": "auto", "border": f"1px solid {COLORS['border']}", "borderRadius": "10px"},
    "style_cell": {
        "textAlign": "left",
        "padding": "14px 16px",
        "fontSize": "0.9375rem",
        "fontFamily": _FONT,
        "fontWeight": "500",
        "color": COLORS["text"],
        "border": "none",
        "borderBottom": f"1px solid {COLORS['border']}",
    },
    "style_header": {
        "backgroundColor": COLORS.get("table_header", COLORS.get("surface_muted", "#EEF3EF")),
        "color": COLORS["text"],
        "fontWeight": "700",
        "fontFamily": _FONT,
        "border": "none",
        "borderBottom": f"1px solid {COLORS['border']}",
    },
    "style_data": {"color": COLORS["text"]},
}

_NUMERIC_COLUMNS = {"co2e_kg", "Valor", "valor", "total", "intensity"}

_SEVERITY_STYLES = [
    {"if": {"filter_query": "{Severidade} = critical"}, "backgroundColor": COLORS["status_danger_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_danger_accent']}"},
    {"if": {"filter_query": "{Severidade} = warning"}, "backgroundColor": COLORS["status_warning_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_warning_accent']}"},
    {"if": {"filter_query": "{Severidade} = success"}, "backgroundColor": COLORS["status_success_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_success_accent']}"},
    {"if": {"filter_query": "{Severidade} = info"}, "backgroundColor": COLORS["status_info_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_info_accent']}"},
]

_INTEGRITY_STYLES = [
    {"if": {"filter_query": '{status} = "divergente"'}, "backgroundColor": COLORS["status_danger_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_danger_accent']}"},
    {"if": {"filter_query": '{status} = "Divergente"'}, "backgroundColor": COLORS["status_danger_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_danger_accent']}"},
    {"if": {"filter_query": '{status} = "integro"'}, "backgroundColor": COLORS["status_success_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_success_accent']}"},
    {"if": {"filter_query": '{status} = "íntegro"'}, "backgroundColor": COLORS["status_success_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_success_accent']}"},
    {"if": {"filter_query": '{status} = "Íntegro"'}, "backgroundColor": COLORS["status_success_bg"], "color": COLORS["text"], "borderLeft": f"3px solid {COLORS['status_success_accent']}"},
]


def _scalar_cell(value: Any) -> str | int | float | bool:
    """DataTable só aceita string, number ou boolean por célula."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _sanitize_records(records: list[dict], columns: list[str] | None = None) -> tuple[list[dict], list[str]]:
    if not records:
        return [], columns or []
    cols = columns or [k for k in records[0].keys() if not str(k).startswith("_")]
    clean = []
    for row in records:
        clean.append({c: _scalar_cell(row.get(c)) for c in cols})
    return clean, cols


def _column_defs(cols: list[str]) -> list[dict]:
    defs = []
    for c in cols:
        col = {"name": c, "id": c}
        if c in _NUMERIC_COLUMNS or c.endswith("_kg"):
            col["type"] = "numeric"
            col["format"] = {"specifier": ",.2f"}
        defs.append(col)
    return defs


def _empty_table(message: str = "Nenhum dado disponível.") -> html.Div:
    return html.Div(
        EmptyState("Sem dados", message, icon="fas fa-table"),
        className="empty-state-container py-2",
    )


def DataTable(
    records: list[dict],
    columns: list[str] | None = None,
    page_size: int = 10,
    extra_conditional: list | None = None,
) -> dash_table.DataTable | html.Div:
    if not records:
        return _empty_table()
    data, cols = _sanitize_records(records, columns)
    if not cols:
        return _empty_table("Nenhuma coluna exibível.")
    conditional = list(_ZEBRA_ROW)
    for c in cols:
        if c in _NUMERIC_COLUMNS or c.endswith("_kg"):
            conditional.append({"if": {"column_id": c}, "textAlign": "right"})
    if extra_conditional:
        conditional.extend(extra_conditional)
    return dash_table.DataTable(
        data=data,
        columns=_column_defs(cols),
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        css=[{"selector": ".dash-table-tooltip", "rule": f"font-family: {_FONT}"}],
        style_data_conditional=conditional,
        **_TABLE_STYLE,
    )


def InsightTable(records: list[dict], columns: list[str] | None = None, page_size: int = 5) -> dash_table.DataTable | html.Div:
    if not records:
        return _empty_table()
    data, cols = _sanitize_records(records, columns)
    style_cond = list(_ZEBRA_ROW)
    if "Severidade" in cols:
        style_cond.extend(_SEVERITY_STYLES)
    return dash_table.DataTable(
        data=data,
        columns=_column_defs(cols),
        page_size=page_size,
        sort_action="native",
        style_data_conditional=style_cond,
        **_TABLE_STYLE,
    )


def IntegrityDataTable(records: list[dict], columns: list[str] | None = None, page_size: int = 20) -> dash_table.DataTable | html.Div:
    return DataTable(records, columns=columns, page_size=page_size, extra_conditional=_INTEGRITY_STYLES)


def DashboardTables(tables: dict) -> html.Div:
    sections = [
        ("Ranking de fontes emissoras", "ranking_sources",
         ["Fonte", "Emissão kg CO₂e", "Participação %", "Variação", "Status"]),
        ("Indicadores por período", "period_indicators",
         ["Período", "Produção de leite", "Emissões kg CO₂e", "kg CO₂e/L", "Status do ciclo", "Integridade"]),
        ("Alertas gerenciais", "management_alerts",
         ["Tipo", "Indicador", "Mensagem", "Severidade", "Período"]),
        ("Auditoria recente", "recent_audit",
         ["Evento", "Etapa", "Status", "Data/hora", "Pacote"]),
    ]
    blocks = []
    for title, key, cols in sections:
        rows = tables.get(key, [])
        blocks.append(html.Div([
            html.H6(title, className="card-title mb-2"),
            InsightTable(rows, columns=cols if rows else None),
        ], className="dashboard-table-block mb-3"))
    return html.Div(blocks)
