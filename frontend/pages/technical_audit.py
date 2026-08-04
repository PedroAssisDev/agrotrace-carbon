"""Hub de Auditoria Técnica — verificação, rastreabilidade e comprovação."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.cycle_select import CycleSelect
from components.empty_state import EmptyFilterState
from components.page_header import PageHeader
from services.page_context import resolve_page_context

_AUDIT_TABS = [
    ("ta-summary", "Resumo da Auditoria"),
    ("ta-timeline", "Linha do Tempo"),
    ("ta-provenance", "Proveniência"),
    ("ta-prov-queries", "Consultas de Proveniência"),
    ("ta-artifacts", "Artefatos"),
    ("ta-blockchain", "Blockchain"),
    ("ta-integrity", "Integridade"),
    ("ta-logs", "Logs e Alertas"),
    ("ta-payload", "Payload Técnico"),
]


def _chrome_children(ctx, filter_options):
    header = PageHeader(
        "Auditoria Técnica",
        "Verificação, rastreabilidade, proveniência e comprovação técnica do ciclo de vida do dado.",
        ctx.global_filter,
        filter_options,
        cycle=ctx.active_cycle,
        show_status=True,
    )
    empty = (
        EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles)
        if ctx.is_empty and not ctx.active_cycle.get("cycle_id")
        else None
    )
    cycle_row = (
        CycleSelect(ctx.cycles, ctx.active_cycle, select_id="filter-cycle-select")
        if ctx.active_cycle.get("cycle_id")
        else []
    )
    return header, empty, cycle_row


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
    active_tab: str = "ta-summary",
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    tab_id = active_tab if active_tab in {t[0] for t in _AUDIT_TABS} else "ta-summary"
    header, empty, cycle_row = _chrome_children(ctx, filter_options)

    body = [
        html.Div(id="ta-page-header", children=header),
        html.Div(id="ta-empty-state", children=empty),
        html.Div(id="ta-cycle-select-row", children=cycle_row),
        dcc.Store(id="ta-prov-events-data", data=[]),
        dcc.Store(id="ta-prov-query-history", storage_type="local"),
        dcc.Store(id="ta-prov-last-result"),
        dcc.Download(id="ta-prov-csv-download"),
        dcc.Download(id="ta-raw-download"),
        dbc.Tabs(
            [dbc.Tab(label=label, tab_id=tab_id) for tab_id, label in _AUDIT_TABS],
            id="technical-audit-tabs",
            active_tab=tab_id,
            className="agro-tabs",
        ),
        dcc.Loading(
            html.Div(id="ta-tab-content", className="pt-3"),
            type="default",
            className="ta-tab-loading",
        ),
    ]

    return html.Div(body, className="page-technical-audit page-content-inner")
