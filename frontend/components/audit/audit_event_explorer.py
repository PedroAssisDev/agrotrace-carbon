"""Explorador de eventos de proveniência com filtros locais."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, html

from components.provenance_timeline import ProvenanceTimeline


def _events_body(events: list[dict]) -> html.Div:
    table_rows = [{
        "event_id": e.get("event_id") or e.get("event_type", "") + (e.get("created_at") or ""),
        "evento": e.get("event_type"),
        "fase": e.get("phase"),
        "servico": e.get("service"),
        "status": e.get("status", "ok"),
        "data": e.get("created_at"),
    } for e in events]

    table = dash_table.DataTable(
        id="ta-prov-events-table",
        columns=[
            {"name": "Evento", "id": "evento"},
            {"name": "Fase", "id": "fase"},
            {"name": "Serviço", "id": "servico"},
            {"name": "Status", "id": "status"},
            {"name": "Data", "id": "data"},
        ],
        data=table_rows,
        row_selectable="single",
        selected_rows=[0] if table_rows else [],
        page_size=15,
        style_table={"overflowX": "auto"},
        style_cell={"fontSize": "0.85rem", "padding": "6px"},
        style_header={"fontWeight": "600"},
    ) if table_rows else html.P("Nenhum evento encontrado.", className="text-muted small")

    return html.Div(
        [
            html.P(f"{len(events)} evento(s) no escopo atual.", className="small text-aux mb-2", id="ta-prov-events-count"),
            html.Div(table, className="table-responsive mb-3"),
            html.H6("Timeline", className="section-subtitle mt-3"),
            ProvenanceTimeline(events[:30]),
        ],
        id="ta-prov-events-body",
    )


def AuditEventExplorer(
    events: list[dict],
    filter_options: dict | None = None,
    *,
    show_global_warning: bool = False,
    global_events_count: int = 0,
    selected_event_id: str | None = None,
) -> html.Div:
    opts = filter_options or {}

    filters = dbc.Row([
        dbc.Col(dbc.Select(id="ta-prov-phase", options=opts.get("phases", []), value="all", size="sm"), md=2),
        dbc.Col(dbc.Select(id="ta-prov-service", options=opts.get("services", []), value="all", size="sm"), md=2),
        dbc.Col(dbc.Select(id="ta-prov-status", options=opts.get("statuses", []), value="all", size="sm"), md=2),
        dbc.Col(dbc.Select(id="ta-prov-event-type", options=opts.get("event_types", []), value="all", size="sm"), md=2),
        dbc.Col(dbc.Input(id="ta-prov-search", placeholder="Buscar…", size="sm", debounce=True), md=4),
    ], className="mb-3 g-2", id="ta-prov-filters-row")

    warning = None
    if show_global_warning:
        warning = dbc.Alert(
            f"Nenhum evento específico encontrado para este ciclo. "
            f"{global_events_count} evento(s) global(is) disponível(is) em seção separada.",
            color="warning",
            className="small py-2",
        )

    return html.Div([
        html.H6("Resumo da proveniência", className="section-subtitle"),
        warning,
        filters,
        _events_body(events),
    ], className="audit-event-explorer", id="ta-event-explorer")
