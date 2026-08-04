"""Callbacks de seleção de ciclo (contexto operacional — não colapsa período analítico)."""

from __future__ import annotations

import logging

from dash import ALL, Input, Output, State, callback, callback_context, no_update

from utils.callback_logging import log_filter_summary
from utils.cycle_helpers import cycle_store_summary
from utils.file_helpers import get_cycle, list_cycles
from utils.global_filter import normalize_filter_state

logger = logging.getLogger("agrotrace.context")


def _sync_from_cycle_id(cycle_id: str | None, global_filter: dict | None):
    if not cycle_id:
        return (no_update,) * 3
    loaded = get_cycle(cycle_id)
    if not loaded:
        return cycle_id, no_update, no_update

    all_cycles = list_cycles()
    prev = normalize_filter_state(global_filter, all_cycles, context_cycle_id=cycle_id)
    raw = {
        "farm_id": loaded.get("property_id") or prev.get("farm_id"),
        "cycle_id": cycle_id,
        "analysis_period_start": prev.get("analysis_period_start"),
        "analysis_period_end": prev.get("analysis_period_end"),
        "view_granularity": prev.get("view_granularity"),
        "data_mode": prev.get("data_mode"),
    }
    normalized = normalize_filter_state(raw, all_cycles, context_cycle_id=cycle_id)
    log_filter_summary(f"[CTX] sync_from_cycle_id cycle={cycle_id}", normalized)
    return (
        normalized.get("cycle_id"),
        cycle_store_summary(loaded),
        normalized,
    )


@callback(
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("global-filter-store", "data", allow_duplicate=True),
    Input("filter-cycle-select", "value", allow_optional=True),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def on_filter_cycle_select(cycle_id, global_filter):
    if not cycle_id:
        return None, no_update, no_update
    result = _sync_from_cycle_id(cycle_id, global_filter)
    if result[0] is no_update:
        return None, no_update, no_update
    return result


@callback(
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("global-filter-store", "data", allow_duplicate=True),
    Input("prov-cycle-filter", "value", allow_optional=True),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def on_prov_cycle_filter(cycle_id, global_filter):
    if not cycle_id:
        return None, no_update
    result = _sync_from_cycle_id(cycle_id, global_filter)
    if result[0] is no_update:
        return None, no_update
    return result[0], result[2]


@callback(
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("global-filter-store", "data", allow_duplicate=True),
    Input("approval-cycle-select", "value", allow_optional=True),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def on_approval_cycle_select(cycle_id, global_filter):
    if not cycle_id:
        return None, no_update, no_update
    result = _sync_from_cycle_id(cycle_id, global_filter)
    if result[0] is no_update:
        return None, no_update, no_update
    return result


@callback(
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("global-filter-store", "data", allow_duplicate=True),
    Input("data-entry-file-select", "value", allow_optional=True),
    Input({"type": "data-entry-detail", "cycle": ALL}, "n_clicks"),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def on_data_entry_file_select(select_value, _clicks, global_filter):
    triggered = callback_context.triggered_id
    cycle_id = select_value
    if isinstance(triggered, dict) and triggered.get("type") == "data-entry-detail":
        cycle_id = triggered.get("cycle")
    if not cycle_id:
        return no_update, no_update, no_update
    result = _sync_from_cycle_id(cycle_id, global_filter)
    if result[0] is no_update:
        return no_update, no_update, no_update
    return result


def register(_app) -> None:
    pass
