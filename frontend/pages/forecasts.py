"""Previsoes de producao e emissoes — gestao de modelos + inferencia."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.agro_tabs import AgroTabs
from components.cards import AlertBox, SectionHeader
from components.empty_state import EmptyFilterState
from components.page_header import PageHeader
from services import model_training_adapter as mta
from services.forecast_view_service import idle_charts_placeholder
from services.model_training_view_service import (
    build_action_bar,
    build_custom_panel,
    build_history_table,
    build_model_cards,
    build_models_header,
    build_retrain_modal,
    build_run_panel,
    family_run_disabled_reason,
    infer_cta_for_family,
)
from services.page_context import resolve_page_context
from utils.global_filter import get_farm_id

_PAGE_TITLE = "Previsões de Produção e Emissões"
_PAGE_SUBTITLE = (
    "Gestão dinâmica de modelos, cenários por rebanho (regressão global) e "
    "projeção histórica mensal por propriedade."
)


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    gf = ctx.global_filter
    farm_id = get_farm_id(gf) or ctx.farm_id

    if ctx.no_farm_selected or not farm_id:
        return html.Div(
            [
                PageHeader(_PAGE_TITLE, _PAGE_SUBTITLE, gf, filter_options),
                EmptyFilterState(no_farm=True),
            ],
            className="page-forecasts page-content-inner",
        )

    property_label = ctx.farm_name or farm_id
    report = mta.get_model_availability(farm_id)
    history = mta.list_training_runs(farm_id)
    active_runs = report.get("active_training_runs") or []
    current_run = active_runs[0] if active_runs else (history[0] if history else None)

    models_tab = dbc.Tab(
        _models_panel(report, property_label, farm_id, history, current_run),
        label="Modelos",
        tab_id="fc-tab-models",
    )
    regression_tab = dbc.Tab(
        _regression_panel(report),
        label="Cenario por rebanho",
        tab_id="fc-tab-regression",
    )
    timeseries_tab = dbc.Tab(
        _timeseries_panel(report),
        label="Projecao historica",
        tab_id="fc-tab-timeseries",
    )

    return html.Div(
        [
            PageHeader(_PAGE_TITLE, _PAGE_SUBTITLE, gf, filter_options, cycle=ctx.active_cycle),
            dcc.Store(id="fc-models-refresh", data=0),
            dcc.Interval(id="fc-training-poll", interval=2000, n_intervals=0, disabled=not bool(active_runs)),
            AgroTabs(
                [models_tab, regression_tab, timeseries_tab],
                id="fc-tabs",
                active_tab="fc-tab-models",
            ),
            build_retrain_modal(),
        ],
        className="page-forecasts page-content-inner",
    )


def _models_panel(report, property_label, farm_id, history, current_run) -> html.Div:
    return html.Div(
        [
            html.Div(id="fc-models-header", children=build_models_header(report, property_label)),
            html.Div(id="fc-model-cards", children=build_model_cards(report)),
            html.Div(id="fc-action-bar", children=build_action_bar(report)),
            build_custom_panel(report, farm_id),
            html.Div(id="fc-run-panel-wrap", children=build_run_panel(current_run)),
            html.Div(id="fc-history-wrap", children=build_history_table(history)),
        ],
        className="pt-3",
    )


def _regression_panel(report: dict) -> html.Div:
    disabled_reason = family_run_disabled_reason(report, "regression")
    run_disabled = bool(disabled_reason)

    return html.Div(
        [
            SectionHeader(
                "Cenario por rebanho",
                "Usa as vacas do ultimo periodo observado e estima producao e emissoes "
                "para o periodo seguinte (mes ou ano).",
            ),
            html.Div(id="fc-regression-cta", children=infer_cta_for_family(report, "regression")),
            html.Small(id="fc-regression-last-hint", className="text-aux d-block mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Granularidade", className="form-label small mb-1"),
                            dcc.Dropdown(
                                id="fc-regression-granularity",
                                options=[
                                    {"label": "Mensal", "value": "monthly"},
                                    {"label": "Anual", "value": "annual"},
                                ],
                                value="monthly",
                                clearable=False,
                                className="mb-2",
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label(
                                id="fc-cows-label",
                                children="Vacas em lactacao esperadas (periodo seguinte)",
                                className="form-label small mb-1",
                            ),
                            dbc.Input(
                                id="fc-expected-cows",
                                type="number",
                                min=0,
                                step=1,
                                placeholder="Ex.: 120",
                                className="mb-2",
                                disabled=run_disabled,
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            html.Label("\u00a0", className="form-label small mb-1 d-block"),
                            dbc.Button(
                                "Calcular previsao",
                                id="fc-regression-run",
                                color="success",
                                className="w-100",
                                disabled=run_disabled,
                                title=disabled_reason or "Calcula o periodo seguinte ao ultimo registro",
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="g-2 align-items-end mb-3",
            ),
            html.Small(disabled_reason, id="fc-regression-disabled-hint", className="text-aux d-block mb-2")
            if disabled_reason
            else html.Div(id="fc-regression-disabled-hint"),
            html.Div(id="fc-regression-feedback"),
            html.Div(
                id="fc-regression-charts",
                children=idle_charts_placeholder(
                    "As vacas do último período são preenchidas automaticamente. "
                    "Clique em Calcular previsão para ver o gráfico."
                ),
            ),
            html.Div(id="fc-regression-kpis"),
            html.Div(id="fc-regression-details"),
        ],
        className="pt-3",
    )


def _timeseries_panel(report: dict) -> html.Div:
    disabled_reason = family_run_disabled_reason(report, "time_series")
    run_disabled = bool(disabled_reason)
    summary = report.get("data_summary") or {}

    notice_extra = html.Small(
        f"Registros mensais da propriedade: {summary.get('property_monthly_records', 0)} "
        f"(minimo {summary.get('min_ts_records', 12)} contiguos).",
        className="text-aux d-block mb-2",
        id="fc-timeseries-records-hint",
    )

    return html.Div(
        [
            SectionHeader(
                "Projeção histórica",
                "Gera a projeção dos próximos 3 meses com base na série temporal mensal "
                "da propriedade — sem variáveis exógenas nem entrada de vacas.",
            ),
            notice_extra,
            html.Div(id="fc-timeseries-cta", children=infer_cta_for_family(report, "time_series")),
            dbc.Button(
                "Gerar projeção",
                id="fc-timeseries-run",
                color="success",
                className="mb-2",
                disabled=run_disabled,
                title=disabled_reason or "Gera projeção dos próximos 3 meses",
            ),
            html.Small(disabled_reason, id="fc-timeseries-disabled-hint", className="text-aux d-block mb-3")
            if disabled_reason
            else html.Div(id="fc-timeseries-disabled-hint", className="mb-3"),
            html.Div(id="fc-timeseries-feedback"),
            html.Div(id="fc-timeseries-table"),
            html.Div(
                id="fc-timeseries-charts",
                children=idle_charts_placeholder(
                    "Clique em Gerar projeção para ver histórico e os próximos 3 meses."
                ),
            ),
            html.Div(id="fc-timeseries-details"),
        ],
        className="pt-3",
    )
