"""Callbacks de gestao dinamica de modelos (aba Modelos).

Callbacks com Inputs globais (url / global-filter) so escrevem em dcc.Store.
Callbacks com Outputs fc-* so usam Inputs que existem na pagina /previsoes.
"""

from __future__ import annotations

from dash import Input, Output, State, callback, ctx, html, no_update
from dash.exceptions import PreventUpdate

from components.cards import AlertBox
from services import model_training_adapter as mta
from services.model_training_view_service import (
    build_action_bar,
    build_history_table,
    build_model_cards,
    build_models_header,
    build_run_panel,
    infer_cta_for_family,
)
from utils.global_filter import get_farm_id


def _safe_kwargs(profile, metric, min_imp, activate_values):
    try:
        min_val = float(min_imp if min_imp is not None else 0)
    except (TypeError, ValueError):
        min_val = 0.0
    if min_val < 0:
        min_val = 0.0
    return {
        "candidate_profile": profile or "core",
        "selection_metric": metric or "mae",
        "minimum_improvement_over_baseline": min_val,
        "activate_after_success": "yes" in (activate_values or []),
    }


@callback(
    Output("model-availability-store", "data"),
    Output("training-history-store", "data"),
    Output("forecast-regression-result-store", "data", allow_duplicate=True),
    Output("forecast-timeseries-result-store", "data", allow_duplicate=True),
    Input("url", "pathname"),
    Input("global-filter-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def sync_model_stores(pathname, global_filter):
    """Somente stores (sempre no layout). Nao toca em fc-* da pagina."""
    if pathname != "/previsoes":
        raise PreventUpdate
    farm_id = get_farm_id(global_filter)
    if not farm_id:
        return None, [], None, None

    report = mta.get_model_availability(farm_id)
    history = mta.list_training_runs(farm_id)
    # limpa previsoes ao entrar/trocar propriedade
    return report, history, None, None


@callback(
    Output("fc-models-header", "children"),
    Output("fc-model-cards", "children"),
    Output("fc-action-bar", "children"),
    Output("fc-history-wrap", "children"),
    Output("fc-regression-cta", "children"),
    Output("fc-timeseries-cta", "children"),
    Input("fc-tabs", "active_tab"),
    Input("fc-models-refresh", "data"),
    State("model-availability-store", "data"),
    State("training-history-store", "data"),
    State("global-filter-store", "data"),
    prevent_initial_call=False,
)
def render_models_ui(active_tab, refresh_tick, report, history, global_filter):
    """Atualiza UI apenas com Inputs da pagina (/previsoes)."""
    if not report:
        raise PreventUpdate
    farm_id = get_farm_id(global_filter)
    label = (global_filter or {}).get("farm_name") or farm_id or "—"
    return (
        build_models_header(report, label),
        build_model_cards(report),
        build_action_bar(report),
        build_history_table(history or []),
        infer_cta_for_family(report, "regression"),
        infer_cta_for_family(report, "time_series"),
    )


@callback(
    Output("training-run-store", "data"),
    Output("fc-training-action-feedback", "children"),
    Output("fc-training-poll", "disabled"),
    Output("fc-retrain-modal", "is_open", allow_duplicate=True),
    Input("fc-ensure-missing", "n_clicks"),
    Input("fc-retrain-stale", "n_clicks"),
    Input("fc-retrain-confirm", "n_clicks"),
    Input("fc-run-custom", "n_clicks"),
    State("global-filter-store", "data"),
    State("model-availability-store", "data"),
    State("fc-candidate-profile", "value"),
    State("fc-selection-metric", "value"),
    State("fc-min-improvement", "value"),
    State("fc-activate-after", "value"),
    State("fc-slot-checklist", "value"),
    prevent_initial_call=True,
)
def start_training(
    n_ensure,
    n_stale,
    n_confirm,
    n_custom,
    global_filter,
    availability,
    profile,
    metric,
    min_imp,
    activate_values,
    selected_ids,
):
    farm_id = get_farm_id(global_filter)
    if not farm_id:
        return no_update, AlertBox("Selecione uma fazenda.", variant="warning"), no_update, no_update

    triggered = ctx.triggered_id
    kwargs = _safe_kwargs(profile, metric, min_imp, activate_values)

    try:
        if triggered == "fc-ensure-missing":
            run = mta.ensure_missing_models(farm_id, **kwargs)
            msg = AlertBox(f"Execucao iniciada: {run.get('run_id')}", variant="success", className="small")
            return run, msg, False, no_update

        if triggered == "fc-retrain-stale":
            run = mta.retrain_stale_models(farm_id, **kwargs)
            msg = AlertBox(f"Atualizacao iniciada: {run.get('run_id')}", variant="success", className="small")
            return run, msg, False, no_update

        if triggered == "fc-retrain-confirm":
            slots = []
            for item in (availability or {}).get("models") or []:
                if item.get("status") in {"available", "stale"} and item.get("eligible"):
                    slots.append(
                        {
                            "family": item["family"],
                            "scope": item["scope"],
                            "granularity": item["granularity"],
                            "target": item["target"],
                            "property_id": item.get("property_id"),
                        }
                    )
            if not slots:
                return no_update, AlertBox("Nenhum modelo elegivel para retreinar.", variant="info"), no_update, False
            run = mta.train_selected_models(farm_id, slots, **kwargs)
            msg = AlertBox(f"Retreinamento iniciado: {run.get('run_id')}", variant="success", className="small")
            return run, msg, False, False

        if triggered == "fc-run-custom":
            slots = mta.resolve_slot_selection(farm_id, selected_ids or [])
            if not slots:
                return no_update, AlertBox("Selecione ao menos um modelo elegivel.", variant="warning"), no_update, no_update
            run = mta.train_selected_models(farm_id, slots, **kwargs)
            msg = AlertBox(f"Treinamento personalizado iniciado: {run.get('run_id')}", variant="success", className="small")
            return run, msg, False, no_update
    except Exception as exc:  # noqa: BLE001
        return no_update, AlertBox(str(exc), variant="danger"), no_update, False

    raise PreventUpdate


@callback(
    Output("fc-retrain-modal", "is_open"),
    Output("fc-retrain-modal-summary", "children"),
    Output("fc-retrain-modal-details", "children"),
    Input("fc-open-retrain-modal", "n_clicks"),
    Input("fc-retrain-cancel", "n_clicks"),
    State("global-filter-store", "data"),
    State("model-availability-store", "data"),
    State("fc-candidate-profile", "value"),
    State("fc-selection-metric", "value"),
    State("fc-activate-after", "value"),
    prevent_initial_call=True,
)
def toggle_retrain_modal(n_open, n_cancel, global_filter, availability, profile, metric, activate_values):
    triggered = ctx.triggered_id
    if triggered == "fc-retrain-cancel":
        return False, no_update, no_update
    farm_id = get_farm_id(global_filter) or "—"
    models = [
        m
        for m in ((availability or {}).get("models") or [])
        if m.get("status") in {"available", "stale"} and m.get("eligible")
    ]
    globals_affected = [m for m in models if m.get("family") == "regression"]
    summary = f"Propriedade: {farm_id}. Modelos selecionados: {len(models)}."
    details = [
        html.P(f"Modelos globais afetados: {len(globals_affected)}"),
        html.P(f"Perfil: {profile or 'core'} · Metrica: {metric or 'mae'}"),
        html.P(f"Ativacao automatica: {'sim' if 'yes' in (activate_values or []) else 'nao'}"),
        html.P("Uma nova versao imutavel sera criada; artefatos anteriores serao preservados."),
    ]
    return True, summary, details


@callback(
    Output("fc-custom-panel", "style"),
    Input("fc-toggle-custom", "n_clicks"),
    State("fc-custom-panel", "style"),
    prevent_initial_call=True,
)
def toggle_custom_panel(n_clicks, style):
    style = dict(style or {})
    if style.get("display") == "none":
        style["display"] = "block"
    else:
        style["display"] = "none"
    return style


@callback(
    Output("fc-run-panel-wrap", "children"),
    Output("fc-training-poll", "disabled", allow_duplicate=True),
    Output("training-run-store", "data", allow_duplicate=True),
    Output("model-availability-store", "data", allow_duplicate=True),
    Output("training-history-store", "data", allow_duplicate=True),
    Output("fc-models-refresh", "data"),
    Input("fc-training-poll", "n_intervals"),
    State("training-run-store", "data"),
    State("global-filter-store", "data"),
    State("fc-models-refresh", "data"),
    prevent_initial_call=True,
)
def poll_training_run(n_intervals, run_store, global_filter, refresh_tick):
    """Poll so atualiza stores + painel; cards via fc-models-refresh (Inputs da pagina)."""
    if not run_store or not run_store.get("run_id"):
        raise PreventUpdate
    run = mta.get_training_run(run_store["run_id"])
    if not run:
        raise PreventUpdate

    farm_id = get_farm_id(global_filter)
    status = run.get("status")
    finished = status in {"completed", "partial", "failed", "cancelled"}
    tick = int(refresh_tick or 0)
    if not finished:
        return build_run_panel(run), False, run, no_update, no_update, no_update

    report = mta.get_model_availability(farm_id) if farm_id else {}
    history = mta.list_training_runs(farm_id) if farm_id else []
    return (
        build_run_panel(run),
        True,
        run,
        report,
        history,
        tick + 1,
    )


def register(_app) -> None:
    pass
