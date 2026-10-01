"""Callbacks do filtro global analítico (navbar: fazenda + período de análise)."""

from __future__ import annotations

import copy
import logging

from dash import Input, Output, State, callback, ctx, no_update

from components.global_filters import _aggregated_status_label, _property_options
from services.filter_service import refresh_filter_options
from utils.callback_logging import log_callback, log_filter_summary
from utils.cycle_helpers import cycle_store_summary, strip_private_keys
from utils.file_helpers import get_cycle, list_cycles
from utils.global_filter import (
    DEFAULT_GLOBAL_FILTER,
    cycle_period,
    format_filter_badge,
    format_period_label,
    format_status_badge_label,
    normalize_filter_state,
    period_in_analysis_range,
)
from utils.temporal_model import CALC_BASE_LABELS

logger = logging.getLogger("agrotrace.filter")

_FILTER_COMPARE_KEYS = (
    "farm_id",
    "cycle_id",
    "analysis_period_start",
    "analysis_period_end",
    "view_granularity",
    "data_mode",
    "period",
)


def _filter_state_equal(left: dict | None, right: dict | None) -> bool:
    if not left and not right:
        return True
    left = left or {}
    right = right or {}
    return all(left.get(key) == right.get(key) for key in _FILTER_COMPARE_KEYS)


def _cycle_store_same(left: dict | None, right: dict | None) -> bool:
    left = left or {}
    right = right or {}
    if left.get("cycle_id") != right.get("cycle_id"):
        return False
    return (
        left.get("updated_at") == right.get("updated_at")
        and left.get("current_status") == right.get("current_status")
        and left.get("publication_status") == right.get("publication_status")
        and left.get("approval_decision") == right.get("approval_decision")
    )

_SYNC_OUTPUTS = (
    Output("global-filter-store", "data"),
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("gf-property-dropdown", "value", allow_duplicate=True),
    Output("gf-analysis-start", "value", allow_duplicate=True),
    Output("gf-analysis-end", "value", allow_duplicate=True),
    Output("gf-view-granularity", "value", allow_duplicate=True),
    Output("gf-data-mode", "value", allow_duplicate=True),
    Output("gf-analysis-start", "options", allow_duplicate=True),
    Output("gf-analysis-end", "options", allow_duplicate=True),
    Output("gf-analysis-start-field", "style", allow_duplicate=True),
    Output("gf-analysis-end-field", "style", allow_duplicate=True),
    Output("gf-period-badge", "children", allow_duplicate=True),
    Output("gf-granularity-badge", "children", allow_duplicate=True),
    Output("gf-status-badge", "children", allow_duplicate=True),
    Output("gf-aggregated-badge", "children", allow_duplicate=True),
    Output("gf-aggregated-badge", "style", allow_duplicate=True),
    Output("filter-options-store", "data", allow_duplicate=True),
)

_SYNC_OUTPUTS_CLEAR = (
    Output("global-filter-store", "data", allow_duplicate=True),
    *_SYNC_OUTPUTS[1:],
)


def _load_active_cycle(normalized: dict) -> dict:
    cycle_id = normalized.get("cycle_id")
    if not cycle_id:
        return {}
    loaded = get_cycle(cycle_id)
    return cycle_store_summary(loaded) if loaded else {}


def _analysis_period_ui_state(normalized: dict, options: dict | None) -> tuple:
    period_opts = (options or {}).get("analysis_periods") or []
    show = len(period_opts) > 1
    style = {"display": "block"} if show else {"display": "none"}
    return (
        normalized.get("analysis_period_start"),
        normalized.get("analysis_period_end"),
        period_opts,
        period_opts,
        style,
        style,
    )


def _badge_children(normalized: dict) -> tuple[str, str, str, str, dict]:
    period_display = normalized.get("period_display_label") or format_period_label(normalized.get("period") or "")
    calc_base = normalized.get("calculation_base_granularity") or normalized.get("granularity")
    calc_label = CALC_BASE_LABELS.get(calc_base or "", "—")
    agg = normalized.get("aggregated_approval_status")
    agg_label = f"Agregado: {_aggregated_status_label(agg)}"
    agg_style = {"display": "inline"} if agg else {"display": "none"}
    return (
        f"Período: {period_display}",
        f"Cálculo: {calc_label}",
        f"Status: {format_status_badge_label(normalized)}",
        agg_label,
        agg_style,
    )


def _build_sync_response(normalized: dict, options: dict) -> tuple:
    active = _load_active_cycle(normalized)
    ap_start, ap_end, ap_opts, ap_opts_end, ap_start_style, ap_end_style = _analysis_period_ui_state(
        normalized, options,
    )
    badges = _badge_children(normalized)
    return (
        normalized,
        normalized.get("cycle_id"),
        active,
        normalized.get("farm_id"),
        ap_start,
        ap_end,
        normalized.get("view_granularity"),
        normalized.get("data_mode"),
        ap_opts,
        ap_opts_end,
        ap_start_style,
        ap_end_style,
        badges[0],
        badges[1],
        badges[2],
        badges[3],
        badges[4],
        options,
    )


def _raw_from_prev(prev: dict) -> dict:
    return {
        "farm_id": prev.get("farm_id"),
        "analysis_period_start": prev.get("analysis_period_start"),
        "analysis_period_end": prev.get("analysis_period_end"),
        "view_granularity": prev.get("view_granularity"),
        "data_mode": prev.get("data_mode"),
        "cycle_id": prev.get("cycle_id"),
    }


@callback(
    *_SYNC_OUTPUTS,
    Input("gf-property-dropdown", "value"),
    Input("gf-analysis-start", "value"),
    Input("gf-analysis-end", "value"),
    Input("gf-view-granularity", "value"),
    Input("gf-data-mode", "value"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
@log_callback("sync_global_filter")
def sync_global_filter(
    farm_id, analysis_start, analysis_end, view_granularity, data_mode,
    current_gf, context_cycle_id,
):
    all_cycles = list_cycles()
    prev = normalize_filter_state(current_gf, all_cycles, context_cycle_id=context_cycle_id)
    raw = _raw_from_prev(prev)

    trigger = ctx.triggered_id
    if trigger == "gf-property-dropdown":
        new_farm = farm_id if isinstance(farm_id, str) and farm_id.strip() else None
        # Remount/espelho do store: farm igual → não limpar períodos nem reescrever stores.
        if new_farm == prev.get("farm_id"):
            return (no_update,) * 18
        raw["farm_id"] = new_farm
        raw["analysis_period_start"] = None
        raw["analysis_period_end"] = None
    elif trigger == "gf-analysis-start":
        raw["analysis_period_start"] = analysis_start
        raw["analysis_period_end"] = analysis_end or prev.get("analysis_period_end")
    elif trigger == "gf-analysis-end":
        raw["analysis_period_start"] = analysis_start or prev.get("analysis_period_start")
        raw["analysis_period_end"] = analysis_end
    elif trigger == "gf-view-granularity":
        raw["view_granularity"] = view_granularity
    elif trigger == "gf-data-mode":
        raw["data_mode"] = data_mode
    else:
        raw["farm_id"] = farm_id if isinstance(farm_id, str) and farm_id.strip() else prev.get("farm_id")
        if view_granularity is not None:
            raw["view_granularity"] = view_granularity
        if data_mode is not None:
            raw["data_mode"] = data_mode

    normalized = normalize_filter_state(raw, all_cycles, context_cycle_id=context_cycle_id)
    if _filter_state_equal(normalized, prev) and trigger != "gf-property-dropdown":
        return (no_update,) * 18
    options = refresh_filter_options(normalized)
    log_filter_summary(f"[FILTER] sync trigger={trigger}", normalized)
    return _build_sync_response(normalized, options)


@callback(
    *_SYNC_OUTPUTS_CLEAR,
    Input("btn-gf-clear", "n_clicks"),
    prevent_initial_call=True,
)
@log_callback("clear_global_filter")
def clear_global_filter(n):
    if not n:
        return (no_update,) * 18
    cleared = copy.deepcopy(DEFAULT_GLOBAL_FILTER)
    options = refresh_filter_options(cleared)
    logger.info("[FILTER] clear_global_filter")
    return _build_sync_response(cleared, options)


@callback(
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("gf-property-dropdown", "value", allow_duplicate=True),
    Output("gf-analysis-start", "value", allow_duplicate=True),
    Output("gf-analysis-end", "value", allow_duplicate=True),
    Output("gf-view-granularity", "value", allow_duplicate=True),
    Output("gf-data-mode", "value", allow_duplicate=True),
    Output("gf-analysis-start", "options", allow_duplicate=True),
    Output("gf-analysis-end", "options", allow_duplicate=True),
    Output("gf-analysis-start-field", "style", allow_duplicate=True),
    Output("gf-analysis-end-field", "style", allow_duplicate=True),
    Output("gf-period-badge", "children", allow_duplicate=True),
    Output("gf-granularity-badge", "children", allow_duplicate=True),
    Output("gf-status-badge", "children", allow_duplicate=True),
    Output("gf-aggregated-badge", "children", allow_duplicate=True),
    Output("gf-aggregated-badge", "style", allow_duplicate=True),
    Input("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    State("cycle-store", "data"),
    State("filter-options-store", "data"),
    State("gf-property-dropdown", "value"),
    State("gf-analysis-start", "value"),
    State("gf-analysis-end", "value"),
    State("gf-view-granularity", "value"),
    State("gf-data-mode", "value"),
    State("gf-analysis-start", "options"),
    State("gf-analysis-end", "options"),
    State("gf-analysis-start-field", "style"),
    State("gf-analysis-end-field", "style"),
    State("gf-period-badge", "children"),
    State("gf-granularity-badge", "children"),
    State("gf-status-badge", "children"),
    State("gf-aggregated-badge", "children"),
    State("gf-aggregated-badge", "style"),
    prevent_initial_call=True,
)
def sync_controls_from_store(
    global_filter,
    context_cycle_id,
    cycle_data,
    filter_options,
    cur_farm,
    cur_ap_start,
    cur_ap_end,
    cur_granularity,
    cur_mode,
    cur_ap_opts,
    cur_ap_opts_end,
    cur_ap_start_style,
    cur_ap_end_style,
    cur_badge_period,
    cur_badge_granularity,
    cur_badge_status,
    cur_badge_agg,
    cur_badge_agg_style,
):
    """Mantém controles UI alinhados quando o store muda por outro callback."""
    all_cycles = list_cycles()
    normalized = normalize_filter_state(global_filter, all_cycles, context_cycle_id=context_cycle_id)
    active = _load_active_cycle(normalized)
    ap_start, ap_end, ap_opts, ap_opts_end, ap_start_style, ap_end_style = _analysis_period_ui_state(
        normalized, filter_options,
    )
    badges = _badge_children(normalized)
    new_ctx = normalized.get("cycle_id")
    ctx_out = no_update if new_ctx == context_cycle_id else new_ctx
    cycle_out = no_update if _cycle_store_same(active, cycle_data) else active

    def _same(a, b):
        return no_update if a == b else a

    return (
        ctx_out,
        cycle_out,
        _same(normalized.get("farm_id"), cur_farm),
        _same(ap_start, cur_ap_start),
        _same(ap_end, cur_ap_end),
        _same(normalized.get("view_granularity"), cur_granularity),
        _same(normalized.get("data_mode"), cur_mode),
        _same(ap_opts, cur_ap_opts),
        _same(ap_opts_end, cur_ap_opts_end),
        _same(ap_start_style, cur_ap_start_style),
        _same(ap_end_style, cur_ap_end_style),
        _same(badges[0], cur_badge_period),
        _same(badges[1], cur_badge_granularity),
        _same(badges[2], cur_badge_status),
        _same(badges[3], cur_badge_agg),
        _same(badges[4], cur_badge_agg_style),
    )


@callback(
    Output("global-filter-store", "data", allow_duplicate=True),
    Output("context-cycle-id", "data", allow_duplicate=True),
    Output("cycle-store", "data", allow_duplicate=True),
    Output("filter-options-store", "data", allow_duplicate=True),
    Input("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
@log_callback("resync_after_pipeline")
def resync_after_pipeline(cycle_data, global_filter, context_cycle_id):
    """Re-normaliza após pipeline — preserva janela analítica quando possível."""
    if not cycle_data or not cycle_data.get("cycle_id"):
        return no_update, no_update, no_update, no_update

    gf = global_filter or {}
    # Atalho: identidade fazenda/ciclo já alinhada — evita list_cycles + normalize
    # (status-only no filtro já era descartado pelo _filter_state_equal).
    if (
        cycle_data.get("cycle_id") == gf.get("cycle_id")
        and cycle_data.get("cycle_id") == context_cycle_id
        and (
            not cycle_data.get("property_id")
            or cycle_data.get("property_id") == gf.get("farm_id")
        )
    ):
        return no_update, no_update, no_update, no_update

    all_cycles = list_cycles()
    prev = normalize_filter_state(global_filter, all_cycles, context_cycle_id=context_cycle_id)
    period = cycle_period(cycle_data)
    ap_start = prev.get("analysis_period_start")
    ap_end = prev.get("analysis_period_end")
    if period and ap_start and ap_end and period_in_analysis_range(period, ap_start, ap_end):
        pass
    elif period and (not ap_start or not ap_end):
        ap_start = ap_start or period
        ap_end = ap_end or period
    elif period:
        ap_start = period
        ap_end = period

    raw = {
        "farm_id": cycle_data.get("property_id") or prev.get("farm_id"),
        "farm_name": cycle_data.get("property_name") or prev.get("farm_name"),
        "cycle_id": cycle_data.get("cycle_id"),
        "analysis_period_start": ap_start,
        "analysis_period_end": ap_end,
        "view_granularity": prev.get("view_granularity"),
        "data_mode": prev.get("data_mode"),
    }
    normalized = normalize_filter_state(raw, all_cycles, context_cycle_id=cycle_data.get("cycle_id"))
    active = _load_active_cycle(normalized) or cycle_store_summary(cycle_data)
    log_filter_summary("[FILTER] resync_after_pipeline", normalized)
    if (
        _filter_state_equal(normalized, global_filter)
        and normalized.get("cycle_id") == context_cycle_id
        and _cycle_store_same(active, cycle_data)
    ):
        return no_update, no_update, no_update, no_update

    # Só recalcula options quando muda fazenda ou ciclo (catálogo/períodos).
    if (
        normalized.get("farm_id") == gf.get("farm_id")
        and normalized.get("cycle_id") == gf.get("cycle_id")
    ):
        options_out = no_update
    else:
        options_out = refresh_filter_options(normalized)
    return normalized, normalized.get("cycle_id"), active, options_out


def _get_farm_id(global_filter):
    from utils.global_filter import get_farm_id
    return get_farm_id(global_filter)


@callback(
    Output("gf-filter-badge", "children"),
    Input("global-filter-store", "data"),
    State("filter-options-store", "data"),
)
def update_filter_badge(global_filter, options):
    return format_filter_badge(global_filter, options or {})


@callback(
    Output("filter-options-store", "data", allow_duplicate=True),
    Input("global-filter-store", "data"),
    State("filter-options-store", "data"),
    prevent_initial_call=True,
)
def refresh_filter_options_on_store(global_filter, current_options):
    """Recarrega options só se a fazenda mudou (sync/clear já atualizam o store)."""
    gf = global_filter or {}
    farm_id = gf.get("farm_id")
    cur = current_options or {}
    # Se options já refletem a fazenda atual (sync_global_filter acabou de setar), não refaz.
    props = cur.get("properties") or []
    cycles = cur.get("cycles") or []
    if farm_id and cycles:
        # Options presentes e tipicamente já refreshados pelo sync — evita cascade.
        # Ainda assim refresh se a lista de properties estiver vazia (bootstrap).
        if props:
            return no_update
    return refresh_filter_options(global_filter)


@callback(
    Output("gf-property-dropdown", "options"),
    Input("filter-options-store", "data"),
)
def sync_property_dropdown_options(options):
    return _property_options((options or {}).get("properties") or [])


def register(_app) -> None:
    pass
