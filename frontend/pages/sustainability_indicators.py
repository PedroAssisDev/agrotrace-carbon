"""Análise Geral — visão analítica consolidada da fazenda no período."""

from __future__ import annotations

from dash import dcc, html

from components.cards import AlertBox
from components.empty_state import EMPTY_NO_OFFICIAL_DATA, EmptyFilterState, EmptyState
from components.page_header import PageHeader
from services import provenance_adapter
from services.dashboard_service import build_dashboard_indicators, build_dashboard_tables
from services.general_analysis_tab_builder import build_general_analysis_tab_content
from services.page_context import resolve_page_context

_PAGE_TITLE = "Análise Geral"
_PAGE_SUBTITLE = "Visão consolidada — produção, emissões, sustentabilidade, qualidade e governança."

_GA_TABS = [
    ("overview", "Visão Geral"),
    ("production", "Produção e Manejo"),
    ("emissions", "Emissões"),
    ("sustainability", "Sustentabilidade"),
    ("quality", "Qualidade dos Dados"),
    ("governance", "Governança e Rastreabilidade"),
]


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)

    if ctx.is_empty:
        return html.Div([
            PageHeader(_PAGE_TITLE, _PAGE_SUBTITLE, ctx.global_filter, filter_options),
            EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles),
        ], className="page-indicators page-content-inner")

    if ctx.no_official_data:
        return html.Div([
            PageHeader(_PAGE_TITLE, _PAGE_SUBTITLE, ctx.global_filter, filter_options, cycle=ctx.active_cycle),
            EmptyState(
                EMPTY_NO_OFFICIAL_DATA["title"],
                EMPTY_NO_OFFICIAL_DATA["message"],
                icon=EMPTY_NO_OFFICIAL_DATA["icon"],
                action_label="Alterar modo de dados",
                action_href="#",
            ),
            AlertBox(
                "Altere o modo de dados na navbar para incluir preliminares.",
                variant="info",
                className="small",
            ),
        ], className="page-indicators page-content-inner")

    work_cycles = ctx.filtered_analysis_cycles or ctx.analysis_cycles
    events = provenance_adapter.list_events_for_context(
        ctx.global_filter, ctx.all_cycles, ctx.active_cycle,
        cycles_in_context=work_cycles, context_cycle_id=context_cycle_id,
    )
    indicators = build_dashboard_indicators(
        work_cycles, ctx.active_cycle, ctx.global_filter, events, ctx.all_cycles,
        temporal=ctx.temporal,
    )
    tables = build_dashboard_tables(indicators)
    bundle = {
        "indicators": indicators,
        "tables": tables,
        "work_cycle_ids": [c.get("cycle_id") for c in work_cycles if c.get("cycle_id")],
    }

    return html.Div([
        PageHeader(_PAGE_TITLE, _PAGE_SUBTITLE, ctx.global_filter, filter_options, cycle=ctx.active_cycle),
        dcc.Store(id="ga-bundle-store", data=bundle),
        dcc.Tabs(
            id="indicators-tabs",
            value="overview",
            className="dashboard-tabs",
            parent_className="dashboard-tabs-bar dashboard-tabs-bar--wrap",
            content_className="dashboard-tab-content",
            children=[
                dcc.Tab(label=label, value=tab_id, className="dashboard-tab", selected_className="dashboard-tab--selected")
                for tab_id, label in _GA_TABS
            ],
        ),
        html.Div(
            id="ga-tab-content",
            children=build_general_analysis_tab_content("overview", indicators, tables, work_cycles),
        ),
    ], className="page-indicators page-content-inner general-analysis-page")
