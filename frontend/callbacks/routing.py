"""Callbacks de roteamento e inicialização."""

from __future__ import annotations

import logging

from dash import Input, Output, State, callback, no_update

from pages.router import render_page
from utils.callback_logging import log_callback
from utils.global_filter import normalize_filter_state

logger = logging.getLogger("agrotrace.callbacks")


def _build_page(
    pathname,
    global_filter,
    upload_feedback,
    cycle_data,
    context_cycle_id,
    filter_options,
    active_audit_tab,
):
    cycle = cycle_data or {}
    from utils.file_helpers import list_cycles

    gf = normalize_filter_state(global_filter, list_cycles(), context_cycle_id=context_cycle_id)
    logger.debug(
        "[CB:display_page] path=%s farm=%s cycle=%s ctx=%s tab=%s",
        pathname,
        gf.get("farm_id"),
        gf.get("cycle_id"),
        context_cycle_id,
        active_audit_tab,
    )
    return render_page(
        pathname,
        cycle,
        gf,
        filter_options or {},
        context_cycle_id,
        upload_feedback,
        active_audit_tab=active_audit_tab or "ta-summary",
    )


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("upload-feedback-store", "data"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    State("filter-options-store", "data"),
    State("ta-active-tab-store", "data"),
)
@log_callback("display_page_route")
def display_page_route(
    pathname,
    upload_feedback,
    cycle_data,
    global_filter,
    context_cycle_id,
    filter_options,
    active_audit_tab,
):
    """Monta a página ao navegar (evita remount completo da Auditoria Técnica no filtro)."""
    return _build_page(
        pathname,
        global_filter,
        upload_feedback,
        cycle_data,
        context_cycle_id,
        filter_options,
        active_audit_tab,
    )


@callback(
    Output("page-content", "children", allow_duplicate=True),
    Input("global-filter-store", "data"),
    State("url", "pathname"),
    State("cycle-store", "data"),
    State("context-cycle-id", "data"),
    State("filter-options-store", "data"),
    State("upload-feedback-store", "data"),
    State("ta-active-tab-store", "data"),
    prevent_initial_call=True,
)
@log_callback("display_page_filter")
def display_page_filter(
    global_filter,
    pathname,
    cycle_data,
    context_cycle_id,
    filter_options,
    upload_feedback,
    active_audit_tab,
):
    """Atualiza páginas gerenciais no filtro; Auditoria Técnica usa callbacks locais."""
    if (pathname or "/") == "/technical-audit":
        return no_update
    return _build_page(
        pathname,
        global_filter,
        upload_feedback,
        cycle_data,
        context_cycle_id,
        filter_options,
        active_audit_tab,
    )


def register(_app) -> None:
    """Import side-effect: callbacks acima registram via @callback."""
