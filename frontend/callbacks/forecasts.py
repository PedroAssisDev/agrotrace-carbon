"""Callbacks da página Previsões (/previsoes)."""

from __future__ import annotations

from dash import Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate

from components.cards import AlertBox
from services.forecast_inference import (
    ForecastInferenceError,
    InvalidInputError,
    ModelNotFoundError,
    get_prediction_facade,
)
from services.forecast_view_service import (
    build_model_details_card,
    build_regression_charts,
    build_regression_kpis,
    build_timeseries_charts,
    build_timeseries_table,
    build_warnings,
    empty_result_message,
)
from utils.global_filter import get_farm_id


@callback(
    Output("forecast-availability-store", "data"),
    Input("url", "pathname"),
    State("global-filter-store", "data"),
    prevent_initial_call=False,
)
def refresh_forecast_availability(pathname, global_filter):
    if pathname != "/previsoes":
        raise PreventUpdate
    farm_id = get_farm_id(global_filter)
    return get_prediction_facade().get_model_availability(farm_id)


@callback(
    Output("fc-cows-label", "children"),
    Input("fc-regression-granularity", "value"),
)
def update_cows_label(granularity):
    if granularity == "annual":
        return "Vacas em lactação esperadas (próximo ano)"
    return "Vacas em lactação esperadas (próximo mês)"


@callback(
    Output("forecast-regression-result-store", "data"),
    Output("fc-regression-feedback", "children"),
    Output("fc-regression-kpis", "children"),
    Output("fc-regression-charts", "children"),
    Output("fc-regression-details", "children"),
    Input("fc-regression-run", "n_clicks"),
    State("fc-regression-granularity", "value"),
    State("fc-expected-cows", "value"),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def run_regression_forecast(n_clicks, granularity, cows, global_filter):
    if not n_clicks:
        raise PreventUpdate
    farm_id = get_farm_id(global_filter)
    if not farm_id:
        msg = AlertBox("Selecione uma fazenda no filtro global.", variant="warning")
        return None, msg, no_update, no_update, no_update

    try:
        result = get_prediction_facade().predict_regression_scenario(
            property_id=farm_id,
            granularity=granularity or "monthly",
            expected_lactating_cows=cows,
        )
    except InvalidInputError as exc:
        return None, AlertBox(str(exc), variant="warning"), "", "", ""
    except ModelNotFoundError as exc:
        return None, AlertBox(str(exc), variant="info"), "", "", ""
    except ForecastInferenceError as exc:
        return None, AlertBox(str(exc), variant="danger"), "", "", ""
    except Exception as exc:  # noqa: BLE001
        return None, AlertBox(f"Falha ao calcular previsão: {exc}", variant="danger"), "", "", ""

    feedback = build_warnings(result.get("warnings"))
    if not feedback.children:
        feedback = AlertBox(
            f"Previsão calculada para {result.get('forecast_period', 'próximo período')}.",
            variant="success",
            className="small",
        )
    return (
        result,
        feedback,
        build_regression_kpis(result),
        build_regression_charts(result),
        build_model_details_card(result.get("models"), title="Detalhes dos modelos de regressão"),
    )


@callback(
    Output("forecast-timeseries-result-store", "data"),
    Output("fc-timeseries-feedback", "children"),
    Output("fc-timeseries-table", "children"),
    Output("fc-timeseries-charts", "children"),
    Output("fc-timeseries-details", "children"),
    Input("fc-timeseries-run", "n_clicks"),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def run_timeseries_forecast(n_clicks, global_filter):
    if not n_clicks:
        raise PreventUpdate
    farm_id = get_farm_id(global_filter)
    if not farm_id:
        msg = AlertBox("Selecione uma fazenda no filtro global.", variant="warning")
        return None, msg, no_update, no_update, no_update

    try:
        result = get_prediction_facade().forecast_time_series(property_id=farm_id)
    except ModelNotFoundError as exc:
        return (
            None,
            AlertBox(str(exc), variant="info"),
            empty_result_message("Sem projeção disponível."),
            "",
            "",
        )
    except ForecastInferenceError as exc:
        return None, AlertBox(str(exc), variant="danger"), "", "", ""
    except Exception as exc:  # noqa: BLE001
        return None, AlertBox(f"Falha ao gerar projeção: {exc}", variant="danger"), "", "", ""

    feedback = build_warnings(result.get("warnings"))
    if not feedback.children:
        feedback = AlertBox(
            "Projeção de 3 meses gerada com sucesso.",
            variant="success",
            className="small",
        )
    return (
        result,
        feedback,
        build_timeseries_table(result),
        build_timeseries_charts(result),
        build_model_details_card(result.get("models"), title="Detalhes dos modelos temporais"),
    )


@callback(
    Output("forecast-ui-store", "data"),
    Input("fc-tabs", "active_tab"),
    State("forecast-ui-store", "data"),
    State("global-filter-store", "data"),
    prevent_initial_call=True,
)
def sync_forecast_ui(active_tab, ui_store, global_filter):
    data = dict(ui_store or {})
    data["active_tab"] = active_tab or "fc-tab-regression"
    data["property_id"] = get_farm_id(global_filter)
    return data


def register(_app) -> None:
    pass
