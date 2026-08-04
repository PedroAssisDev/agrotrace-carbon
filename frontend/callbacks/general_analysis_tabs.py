"""Callbacks de abas lazy da Análise Geral."""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update

from services.general_analysis_tab_builder import build_general_analysis_tab_content
from utils.file_helpers import list_cycles


def _cycles_by_ids(cycle_ids: list[str] | None) -> list[dict]:
    if not cycle_ids:
        return []
    wanted = set(cycle_ids)
    return [c for c in list_cycles() if c.get("cycle_id") in wanted]


@callback(
    Output("ga-tab-content", "children"),
    Input("indicators-tabs", "value"),
    Input("ga-bundle-store", "data"),
    prevent_initial_call=False,
)
def render_general_analysis_tab(active_tab, bundle):
    if not bundle:
        return no_update
    indicators = bundle.get("indicators") or {}
    tables = bundle.get("tables") or {}
    work_cycles = _cycles_by_ids(bundle.get("work_cycle_ids"))
    return build_general_analysis_tab_content(active_tab or "overview", indicators, tables, work_cycles)


def register(_app) -> None:
    pass
