"""Callbacks da tela Revisão e Aprovação por cálculo."""

from __future__ import annotations

import logging

from dash import ALL, Input, Output, State, callback, ctx, no_update

from components.calculation_review.calculation_item_review_panel import CalculationItemReviewPanel
from services.calculation_approval_service import (
    apply_factor_edits,
    approve_item,
    approve_with_zero,
    finalize_file_approval,
    reject_item,
    request_correction,
)
from services.calculation_review_service import ensure_calculation_review, get_review_item
from services.page_context import resolve_page_context
from utils.cycle_helpers import cycle_store_summary, ensure_full_cycle
from utils.file_helpers import save_cycle
from utils.pipeline_logging import ids_from_cycle, log_decision, timed_op

logger = logging.getLogger("agrotrace.calculation_review")


def _active_cycle(cycle_data, global_filter, context_cycle_id):
    ctx_obj = resolve_page_context(cycle_data or {}, global_filter, context_cycle_id)
    return ctx_obj.active_cycle


def _working_cycle(cycle_data, global_filter, context_cycle_id, approval_cycle_id=None):
    """Ciclo completo para mutações — carrega do disco se o store tiver apenas resumo."""
    stored = cycle_data or {}
    full = ensure_full_cycle(stored)
    if full.get("cycle_id") and full.get("calculation"):
        return ensure_calculation_review(dict(full))
    ctx_id = context_cycle_id or approval_cycle_id
    active = _active_cycle(stored, global_filter, ctx_id)
    if active.get("cycle_id"):
        return ensure_calculation_review(dict(active))
    return {}


def _resolve_selected_item(table_data, selected_rows):
    if not table_data:
        return None, None
    idx = selected_rows[0] if selected_rows else 0
    if idx < 0 or idx >= len(table_data):
        return None, None
    row = table_data[idx]
    return row.get("calculation_item_id"), row.get("formula_id")


@callback(
    Output("cr-selected-item-store", "data"),
    Input("cr-items-table", "selected_rows", allow_optional=True),
    State("cr-items-table", "data", allow_optional=True),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def select_review_item(selected_rows, table_data, pathname):
    if (pathname or "/") != "/approval":
        return no_update
    item_id, _ = _resolve_selected_item(table_data, selected_rows)
    return item_id if item_id else no_update


@callback(
    Output("cr-detail-panel", "children"),
    Input("cr-items-table", "selected_rows", allow_optional=True),
    Input("url", "pathname"),
    Input("cycle-store", "data"),
    Input("global-filter-store", "data"),
    Input("context-cycle-id", "data"),
    Input("approval-cycle-select", "value"),
    State("cr-items-table", "data", allow_optional=True),
    State("filter-options-store", "data"),
    prevent_initial_call=False,
)
def update_detail_panel(
    selected_rows,
    pathname,
    cycle_data,
    global_filter,
    context_cycle_id,
    approval_cycle_id,
    table_data,
    _filter_options,
):
    if pathname != "/approval":
        return no_update

    cycle = _active_cycle(cycle_data, global_filter, context_cycle_id or approval_cycle_id)
    if not cycle.get("cycle_id"):
        return no_update

    cycle = ensure_calculation_review(dict(cycle))
    item_id, formula_id = _resolve_selected_item(table_data, selected_rows)
    if not item_id and not formula_id:
        items = (cycle.get("calculation_review") or {}).get("items") or []
        if items:
            item_id = items[0].get("calculation_item_id")
            formula_id = items[0].get("formula_id")

    item = get_review_item(cycle, item_id, formula_id=formula_id)
    if not item:
        return CalculationItemReviewPanel(cycle, None)
    return CalculationItemReviewPanel(cycle, item.get("calculation_item_id"))


@callback(
    Output("cr-hash-collapse", "is_open"),
    Input("cr-toggle-hash", "n_clicks"),
    State("cr-hash-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_hash(n, is_open):
    if not n:
        return no_update
    return not is_open


def _save_and_return(cycle: dict) -> dict:
    save_cycle(cycle)
    return cycle_store_summary(cycle)


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Output("cr-item-action-feedback", "children"),
    Input("cr-btn-approve-item", "n_clicks"),
    Input("cr-btn-approve-zero", "n_clicks"),
    Input("cr-btn-reject-item", "n_clicks"),
    Input("cr-btn-request-correction", "n_clicks"),
    State("cr-selected-item-store", "data"),
    State("cr-reviewer", "value"),
    State("cr-justification", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    State("approval-cycle-select", "value"),
    prevent_initial_call=True,
)
def item_decision_cb(n_ok, n_zero, n_reject, n_corr, item_id, reviewer, justification, cycle_data, global_filter, context_cycle_id, approval_cycle_id):
    if not item_id or not any((n_ok, n_zero, n_reject, n_corr)):
        return no_update, no_update

    cycle = _working_cycle(cycle_data, global_filter, context_cycle_id, approval_cycle_id)
    if not cycle.get("cycle_id"):
        return no_update, "Ciclo não encontrado."

    triggered = ctx.triggered_id
    try:
        if triggered == "cr-btn-approve-item":
            cycle = approve_item(cycle, item_id, reviewer=reviewer or "Revisor", justification=justification or "")
            msg = "Item aprovado."
        elif triggered == "cr-btn-approve-zero":
            cycle = approve_with_zero(cycle, item_id, reviewer=reviewer or "Revisor", justification=justification or "")
            msg = "Item aprovado com zero confirmado."
        elif triggered == "cr-btn-reject-item":
            cycle = reject_item(cycle, item_id, reviewer=reviewer or "Revisor", justification=justification or "")
            msg = "Item rejeitado."
        elif triggered == "cr-btn-request-correction":
            cycle = request_correction(cycle, item_id, reviewer=reviewer or "Revisor", justification=justification or "")
            msg = "Correção solicitada."
        else:
            return no_update, no_update
        return _save_and_return(cycle), msg
    except Exception as exc:
        logger.exception("Erro na decisão do item: %s", exc)
        return no_update, str(exc)


@callback(
    Output("cr-factor-methodology", "disabled"),
    Output("cr-factor-methodology", "value"),
    Input({"type": "cr-factor-input", "group": ALL, "key": ALL}, "value"),
    State({"type": "cr-factor-input", "group": ALL, "key": ALL}, "id"),
    State("cr-factor-baseline-store", "data"),
    prevent_initial_call=False,
)
def toggle_factor_methodology_cb(values, ids, baseline_data):
    store = baseline_data or {}
    baseline = store.get("baseline") or []
    default_meth = store.get("default_methodology") or "IPCC/IDF-compatible"
    applied_meth = store.get("applied_methodology")

    baseline_map = {
        (b["group"], b["factor_key"]): float(b["value"])
        for b in baseline
    }
    changed = False
    for fid, val in zip(ids or [], values or []):
        if not fid or val is None or val == "":
            continue
        key = (fid["group"], fid["key"])
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if key not in baseline_map or baseline_map[key] != num:
            changed = True
            break

    if changed:
        return False, default_meth
    return True, applied_meth or default_meth


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Output("cr-item-action-feedback", "children", allow_duplicate=True),
    Input("cr-btn-apply-factors", "n_clicks"),
    State("cr-selected-item-store", "data"),
    State({"type": "cr-factor-input", "group": ALL, "key": ALL}, "value"),
    State({"type": "cr-factor-input", "group": ALL, "key": ALL}, "id"),
    State("cr-factor-methodology", "value"),
    State("cr-factor-baseline-store", "data"),
    State("cr-reviewer", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    State("approval-cycle-select", "value"),
    prevent_initial_call=True,
)
def apply_factors_cb(
    n,
    item_id,
    factor_values,
    factor_ids,
    methodology_note,
    baseline_data,
    reviewer,
    cycle_data,
    global_filter,
    context_cycle_id,
    approval_cycle_id,
):
    if not n or not item_id:
        return no_update, no_update

    cycle = _working_cycle(cycle_data, global_filter, context_cycle_id, approval_cycle_id)
    if not cycle.get("cycle_id"):
        return no_update, "Ciclo não encontrado."

    edits: list[dict] = []
    for fid, val in zip(factor_ids or [], factor_values or []):
        if not fid or val is None or val == "":
            continue
        try:
            edits.append({
                "group": fid["group"],
                "factor_key": fid["key"],
                "value": float(val),
            })
        except (TypeError, ValueError):
            return no_update, f"Valor inválido para {fid.get('key')}."

    if not edits:
        return no_update, "Informe ao menos um fator."

    from services.calculation_factor_mapping_service import split_changed_factor_edits

    baseline = (baseline_data or {}).get("baseline") or []
    changed_edits, _ = split_changed_factor_edits(baseline, edits)
    if not changed_edits:
        return no_update, "Nenhum fator foi alterado."

    try:
        cycle = apply_factor_edits(
            cycle, item_id,
            edits=edits,
            reviewer=reviewer or "Revisor",
            methodology=methodology_note,
            factors_changed=True,
        )
        return _save_and_return(cycle), "Fatores aplicados. Reaprove o item após revisar o resultado."
    except Exception as exc:
        logger.exception("Erro ao aplicar fatores: %s", exc)
        return no_update, str(exc)


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Output("cr-finalize-feedback", "children"),
    Input("cr-btn-finalize", "n_clicks"),
    State("cr-reviewer", "value"),
    State("cr-justification", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    State("approval-cycle-select", "value"),
    prevent_initial_call=True,
)
def finalize_cb(n, reviewer, justification, cycle_data, global_filter, context_cycle_id, approval_cycle_id):
    if not n:
        return no_update, no_update

    cycle = _working_cycle(cycle_data, global_filter, context_cycle_id, approval_cycle_id)
    if not cycle.get("cycle_id"):
        return no_update, "Ciclo não encontrado."
    log_decision(
        logger,
        "finalize_start",
        **ids_from_cycle(cycle),
        reviewer=reviewer or "Revisor",
    )
    try:
        with timed_op() as timer:
            cycle = finalize_file_approval(cycle, reviewer=reviewer or "Revisor", justification=justification or "")
            log_decision(
                logger,
                "finalize_done",
                **ids_from_cycle(cycle),
                status=cycle.get("current_status"),
                duration_ms=timer.duration_ms,
            )
        return _save_and_return(cycle), "Aprovação final concluída. Publicação e blockchain iniciados."
    except Exception as exc:
        logger.exception("Erro ao finalizar aprovação: %s", exc)
        return no_update, str(exc)


def register(_app) -> None:
    pass
