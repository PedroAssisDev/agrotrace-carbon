"""Callbacks da seção Consultas de Proveniência (Auditoria Técnica)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, html, no_update, ALL, ctx as dash_ctx

from services.page_context import resolve_page_context
from services.provenance_query_service import (
    apply_context_placeholders,
    build_query_context_from_cycle,
    execute_provenance_query,
    rows_to_csv,
)
from services.provenance_query_templates import get_template_by_id
from services.provenance_sql_validator import format_sql_simple

logger = logging.getLogger("agrotrace.provenance_queries")

MAX_HISTORY = 20


def _ctx_from_stores(cycle_data, global_filter, context_cycle_id):
    return resolve_page_context(cycle_data, global_filter, context_cycle_id)


def _query_context(ctx) -> dict[str, str]:
    return build_query_context_from_cycle(ctx.active_cycle, ctx.farm_id)


def _render_results(result: dict) -> html.Div:
    if result.get("error"):
        return dbc.Alert(result["error"], color="danger", className="small")

    columns = result.get("columns") or []
    rows = result.get("rows") or []
    if not rows:
        return html.P(
            "Nenhum registro encontrado para a consulta executada.",
            className="text-muted small prov-empty-result",
        )

    table = dash_table.DataTable(
        id="ta-prov-results-datatable",
        columns=[{"name": c, "id": c} for c in columns],
        data=rows,
        page_size=25,
        style_table={"overflowX": "auto"},
        style_cell={"fontSize": "0.8rem", "padding": "6px", "maxWidth": "280px", "overflow": "hidden", "textOverflow": "ellipsis"},
        style_header={"fontWeight": "600"},
    )
    parts = [html.Div(table, className="table-responsive")]
    if result.get("truncated"):
        parts.append(dbc.Alert(
            "Resultado truncado pelo limite máximo de linhas.",
            color="warning",
            className="small py-2 mt-2",
        ))
    return html.Div(parts)


def _render_meta(result: dict) -> html.Div:
    if result.get("error"):
        return html.Div()
    return html.Div([
        html.Span(f"{result.get('row_count', 0)} registro(s)", className="badge bg-light text-dark me-2"),
        html.Span(f"{result.get('execution_time_ms', 0)} ms", className="badge bg-light text-dark me-2"),
        html.Span(f"LIMIT {result.get('limit', 100)}", className="badge bg-light text-dark me-2"),
        html.Span(f"OFFSET {result.get('offset', 0)}", className="badge bg-light text-dark"),
    ], className="prov-query-meta small")


def _render_history(history: list | None) -> html.Div:
    if not history:
        return html.P("Nenhuma consulta executada ainda.", className="text-muted small")
    items = []
    for idx, entry in enumerate(history[:MAX_HISTORY]):
        label = (entry.get("sql") or "")[:80].replace("\n", " ")
        status = "OK" if entry.get("ok") else "Erro"
        color = "success" if entry.get("ok") else "danger"
        items.append(
            dbc.Button(
                [
                    html.Span(f"{entry.get('at', '')} ", className="text-muted"),
                    html.Span(label),
                    dbc.Badge(status, color=color, className="ms-2"),
                    dbc.Badge(f"{entry.get('rows', 0)} linhas", color="light", text_color="dark", className="ms-1"),
                ],
                id={"type": "ta-prov-history-item", "index": idx},
                color="link",
                className="text-start d-block prov-history-item mb-1 p-0",
                size="sm",
            )
        )
    return html.Div(items)


def _append_history(history: list | None, entry: dict) -> list:
    hist = list(history or [])
    hist.insert(0, entry)
    return hist[:MAX_HISTORY]


def _build_filter_clause(
    event_type, entity_type, artifact, result_set, status, hash_val, entity_id, date_from, date_to,
) -> str:
    parts: list[str] = []
    if event_type:
        parts.append(f"event_type = '{event_type}'")
    if entity_type:
        parts.append(f"aggregate_kind = '{entity_type}'")
    if artifact:
        parts.append(f"source_artifact_id = '{artifact}'")
    if result_set:
        parts.append(f"calculation_result_set_id = '{result_set}'")
    if status:
        parts.append(f"status = '{status}'")
    if hash_val:
        parts.append(f"hash_value LIKE '%{hash_val}%'")
    if entity_id:
        parts.append(f"aggregate_id = '{entity_id}'")
    if date_from:
        parts.append(f"created_at >= '{date_from}'")
    if date_to:
        parts.append(f"created_at <= '{date_to} 23:59:59'")
    if not parts:
        return ""
    return "\nAND " + "\nAND ".join(parts)


@callback(
    Output("ta-prov-sql-input", "value", allow_duplicate=True),
    Input("ta-prov-apply-template", "n_clicks"),
    State("ta-prov-template-select", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def apply_template(n_clicks, template_id, cycle_data, global_filter, context_cycle_id):
    if not template_id:
        return no_update
    tpl = get_template_by_id(template_id)
    if not tpl:
        return no_update
    ctx = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    return apply_context_placeholders(tpl["sql"], _query_context(ctx))


@callback(
    Output("ta-prov-sql-input", "value", allow_duplicate=True),
    Input("ta-prov-clear-sql", "n_clicks"),
    prevent_initial_call=True,
)
def clear_sql(n_clicks):
    return ""


@callback(
    Output("ta-prov-sql-input", "value", allow_duplicate=True),
    Input("ta-prov-format-sql", "n_clicks"),
    State("ta-prov-sql-input", "value"),
    prevent_initial_call=True,
)
def format_sql(n_clicks, sql):
    return format_sql_simple(sql or "")


@callback(
    Output("ta-prov-sql-input", "value", allow_duplicate=True),
    Input("ta-prov-apply-filters", "n_clicks"),
    State("ta-prov-sql-input", "value"),
    State("ta-prov-filter-event-type", "value"),
    State("ta-prov-filter-entity-type", "value"),
    State("ta-prov-filter-artifact", "value"),
    State("ta-prov-filter-result-set", "value"),
    State("ta-prov-filter-status", "value"),
    State("ta-prov-filter-hash", "value"),
    State("ta-prov-filter-entity-id", "value"),
    State("ta-prov-filter-date-from", "value"),
    State("ta-prov-filter-date-to", "value"),
    prevent_initial_call=True,
)
def apply_filters(n_clicks, sql, event_type, entity_type, artifact, result_set, status, hash_val, entity_id, date_from, date_to):
    clause = _build_filter_clause(event_type, entity_type, artifact, result_set, status, hash_val, entity_id, date_from, date_to)
    if not clause:
        return no_update
    base = (sql or "").rstrip().rstrip(";")
    if "WHERE" in base.upper():
        return base + clause
    return base + "\nWHERE 1=1" + clause


@callback(
    Output("ta-prov-results-table", "children"),
    Output("ta-prov-query-meta", "children"),
    Output("ta-prov-last-result", "data"),
    Output("ta-prov-query-history", "data"),
    Input("ta-prov-run-query", "n_clicks"),
    State("ta-prov-sql-input", "value"),
    State("ta-prov-limit-input", "value"),
    State("ta-prov-query-history", "data"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def run_query(n_clicks, sql, limit, history, cycle_data, global_filter, context_cycle_id):
    ctx = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    qctx = _query_context(ctx)
    effective_limit = int(limit) if limit else 100
    result = execute_provenance_query(
        sql or "",
        limit=effective_limit,
        offset=0,
        context=qctx,
    )
    entry = {
        "sql": sql or "",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "ms": result.get("execution_time_ms", 0),
        "rows": result.get("row_count", 0),
        "ok": result.get("ok", False),
        "error": result.get("error"),
    }
    new_history = _append_history(history, entry)
    return _render_results(result), _render_meta(result), result, new_history


@callback(
    Output("ta-prov-history-list", "children"),
    Input("ta-prov-query-history", "data"),
)
def refresh_history_list(history):
    return _render_history(history)


@callback(
    Output("ta-prov-sql-input", "value", allow_duplicate=True),
    Input({"type": "ta-prov-history-item", "index": ALL}, "n_clicks"),
    State("ta-prov-query-history", "data"),
    prevent_initial_call=True,
)
def restore_from_history(n_clicks_list, history):
    if not history or not n_clicks_list or not any(n_clicks_list):
        return no_update
    if not dash_ctx.triggered_id or not isinstance(dash_ctx.triggered_id, dict):
        return no_update
    idx = dash_ctx.triggered_id.get("index")
    if idx is None or idx >= len(history):
        return no_update
    return history[idx].get("sql", "")


@callback(
    Output("ta-prov-csv-download", "data"),
    Input("ta-prov-export-csv", "n_clicks"),
    State("ta-prov-last-result", "data"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, last_result):
    if not last_result or not last_result.get("rows"):
        return no_update
    content = rows_to_csv(last_result.get("columns") or [], last_result.get("rows") or [])
    return dict(content=content, filename="provenance_query.csv")


def register(_app) -> None:
    pass
