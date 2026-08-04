"""Helpers compartilhados para abas de indicadores."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.cards import KpiGrid, SectionHeader
from components.conditional_widgets import ConditionalChartSection
from components.empty_state import EMPTY_NO_INDICATOR_DATA, EmptyState


def chart_row(children: list, md: int = 6) -> dbc.Row:
    valid = [c for c in children if c is not None]
    if not valid:
        return dbc.Row()
    return dbc.Row([dbc.Col(c, md=md, className="mb-2") for c in valid], className="g-2")


def _tab_empty_state() -> html.Div:
    return html.Div(
        EmptyState(
            EMPTY_NO_INDICATOR_DATA["title"],
            EMPTY_NO_INDICATOR_DATA["message"],
            icon=EMPTY_NO_INDICATOR_DATA["icon"],
            action_label="Revisar aprovação",
            action_href="/approval",
        ),
        className="empty-state-container py-3",
    )


def section_body(kpis: list[dict], charts: list, extra=None) -> list:
    body: list = []
    if kpis:
        body.append(KpiGrid(kpis, col_md=3))
    chart_block = ConditionalChartSection(charts)
    if chart_block.children:
        body.append(chart_block)
    if extra:
        body.append(extra)
    if not body:
        body.append(_tab_empty_state())
    return body


def build_indicator_tabs(sections: list[tuple[str, str, str | None, list]]) -> dcc.Tabs:
    def _panel(content, panel_title: str | None = None) -> html.Div:
        children: list = []
        if panel_title:
            children.append(SectionHeader(panel_title))
        if isinstance(content, list):
            children.extend(content)
        else:
            children.append(content)
        return html.Div(children, className="dashboard-tab-panel")

    return dcc.Tabs(
        id="indicators-tabs",
        value=sections[0][0] if sections else "prod",
        className="dashboard-tabs",
        parent_className="dashboard-tabs-bar dashboard-tabs-bar--wrap",
        content_className="dashboard-tab-content",
        children=[
            dcc.Tab(
                label=label,
                value=tab_id,
                className="dashboard-tab",
                selected_className="dashboard-tab--selected",
                children=_panel(body, panel_title),
            )
            for tab_id, label, panel_title, body in sections
        ],
    )
