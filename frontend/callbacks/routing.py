"""Callbacks de roteamento e inicialização."""

from __future__ import annotations

from dash import Input, Output, callback

from pages.router import render_page
from utils.file_helpers import list_cycles
from utils.global_filter import normalize_filter_state


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("cycle-store", "data"),
    Input("global-filter-store", "data"),
    Input("context-cycle-id", "data"),
    Input("filter-options-store", "data"),
)
def display_page(pathname, cycle_data, global_filter, context_cycle_id, filter_options):
    cycle = cycle_data or {}
    gf = normalize_filter_state(global_filter, list_cycles(), context_cycle_id=context_cycle_id)
    return render_page(pathname, cycle, gf, filter_options or {}, context_cycle_id)


@callback(
    Output("cycle-store", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def init_cycle_store(_pathname):
    return {}


def register(_app) -> None:
    """Import side-effect: callbacks acima registram via @callback."""
