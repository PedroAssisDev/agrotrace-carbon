"""DTOs de UI para a página Previsões."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from dash import dcc, html
import dash_bootstrap_components as dbc

from components.cards import AlertBox, KpiGrid, SectionHeader
from components.charts import apply_chart_theme
from components.status_badges import FilterBadge
from layout.theme import COLORS
from utils.formatting import format_co2e_t, format_liters, format_number

_CHART_CONFIG = {"displayModeBar": False, "responsive": True}


def build_availability_badges(availability: dict[str, Any] | None, property_label: str) -> list:
    availability = availability or {}
    badges: list = [FilterBadge(property_label or "Propriedade")]

    if not availability.get("registry_ok"):
        badges.append(FilterBadge("Sem registry de modelos"))
        return badges

    reg = availability.get("regression") or {}
    monthly = bool((reg.get("monthly") or {}).get("milk_production_liters") or (reg.get("monthly") or {}).get(
        "total_ghg_emissions_tco2e"
    ))
    annual = bool((reg.get("annual") or {}).get("milk_production_liters") or (reg.get("annual") or {}).get(
        "total_ghg_emissions_tco2e"
    ))
    badges.append(FilterBadge("Regressão mensal: disponível" if monthly else "Regressão mensal: indisponível"))
    badges.append(FilterBadge("Regressão anual: disponível" if annual else "Regressão anual: indisponível"))
    badges.append(
        FilterBadge(
            "Série temporal: disponível"
            if availability.get("has_property_timeseries")
            else "Série temporal: sem modelo desta propriedade"
        )
    )
    created = availability.get("latest_created_at")
    if created:
        badges.append(FilterBadge(f"Último treino: {str(created)[:19].replace('T', ' ')}"))
    return badges


def build_regression_kpis(result: dict[str, Any] | None) -> html.Div:
    if not result:
        return html.Div()
    milk = result.get("predicted_milk_production_liters")
    emissions = result.get("predicted_total_ghg_emissions_tco2e")
    intensity = result.get("derived_intensity_tco2e_per_liter")
    metrics = [
        {
            "title": "Produção de leite prevista",
            "value": format_liters(milk) if milk is not None else "—",
            "subtitle": f"Período: {result.get('forecast_period', '—')}",
            "icon": "fas fa-tint",
            "color": "info",
        },
        {
            "title": "Emissões previstas",
            "value": format_co2e_t(emissions) if emissions is not None else "—",
            "subtitle": f"{result.get('expected_lactating_cows', '—')} vacas em lactação",
            "icon": "fas fa-cloud",
            "color": "warning",
        },
    ]
    if intensity is not None:
        metrics.append(
            {
                "title": "Intensidade (derivada)",
                "value": f"{format_number(intensity, 6)} t CO₂e/L",
                "subtitle": "Indicador derivado — não é saída do modelo",
                "icon": "fas fa-balance-scale",
                "color": "secondary",
            }
        )
    return html.Div([KpiGrid(metrics, col_md=4 if intensity is not None else 6)])


def build_regression_charts(result: dict[str, Any] | None) -> html.Div:
    if not result:
        return html.Div()
    history = result.get("history") or []
    period_label = result.get("forecast_period") or "Previsto"
    milk_pred = result.get("predicted_milk_production_liters")
    emis_pred = result.get("predicted_total_ghg_emissions_tco2e")

    milk_fig = _observed_plus_forecast_figure(
        title="Produção de leite — observado e previsto",
        history=history,
        value_key="milk_production_liters",
        forecast_label=period_label,
        forecast_value=milk_pred,
        yaxis_title="Litros",
    )
    emis_fig = _observed_plus_forecast_figure(
        title="Emissões — observado e previsto",
        history=history,
        value_key="total_ghg_emissions_tco2e",
        forecast_label=period_label,
        forecast_value=emis_pred,
        yaxis_title="t CO₂e",
    )
    return dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=milk_fig, config=_CHART_CONFIG, className="dashboard-chart"), md=6),
            dbc.Col(dcc.Graph(figure=emis_fig, config=_CHART_CONFIG, className="dashboard-chart"), md=6),
        ],
        className="g-3 mb-3",
    )


def build_model_details_card(models: dict[str, Any] | None, *, title: str = "Detalhes do modelo") -> html.Div:
    models = models or {}
    if not models:
        return html.Div()
    lines: list = []
    labels = {
        "milk_production_liters": "Produção de leite",
        "total_ghg_emissions_tco2e": "Emissões de GEE",
    }
    for key, label in labels.items():
        meta = models.get(key)
        if not meta:
            continue
        metrics = meta.get("metrics") or {}
        rmse = metrics.get("rmse")
        mae = metrics.get("mae")
        lines.append(
            html.Li(
                [
                    html.Strong(f"{label}: "),
                    html.Span(
                        f"{meta.get('model_id') or '—'} "
                        f"(v{meta.get('version') or '—'}, "
                        f"{meta.get('selected_candidate') or '—'})"
                    ),
                    html.Br(),
                    html.Small(
                        f"RMSE={format_number(rmse) if rmse is not None else '—'} · "
                        f"MAE={format_number(mae) if mae is not None else '—'}",
                        className="text-aux",
                    ),
                ]
            )
        )
    if not lines:
        return html.Div()
    return dbc.Card(
        dbc.CardBody(
            [
                SectionHeader(title, "Metadados técnicos dos artefatos usados na previsão."),
                html.Ul(lines, className="mb-0 small"),
            ]
        ),
        className="agro-card mb-3",
    )


def build_warnings(warnings: list[str] | None) -> html.Div:
    if not warnings:
        return html.Div()
    return html.Div(
        [AlertBox(msg, variant="warning", className="small") for msg in warnings],
        className="mb-2",
    )


def build_timeseries_table(result: dict[str, Any] | None) -> html.Div:
    if not result:
        return html.Div()
    periods = result.get("periods") or []
    milk = result.get("milk_predictions") or [None] * len(periods)
    emis = result.get("emission_predictions") or [None] * len(periods)
    header = html.Tr(
        [
            html.Th("Período"),
            html.Th("Produção prevista (L)"),
            html.Th("Emissões previstas (t CO₂e)"),
        ]
    )
    rows = []
    for i, period in enumerate(periods):
        m = milk[i] if i < len(milk) else None
        e = emis[i] if i < len(emis) else None
        rows.append(
            html.Tr(
                [
                    html.Td(period),
                    html.Td(format_liters(m) if m is not None else "—"),
                    html.Td(format_co2e_t(e) if e is not None else "—"),
                ]
            )
        )
    return dbc.Card(
        dbc.CardBody(
            [
                SectionHeader("Projeção de 3 períodos", "Horizonte fixo do modelo temporal mensal."),
                dbc.Table(
                    [html.Thead(header), html.Tbody(rows)],
                    bordered=True,
                    hover=True,
                    size="sm",
                    className="mb-0",
                ),
            ]
        ),
        className="agro-card mb-3",
    )


def build_timeseries_charts(result: dict[str, Any] | None) -> html.Div:
    if not result:
        return html.Div()
    histories = result.get("history") or {}
    periods = result.get("periods") or []
    milk_hist = histories.get("milk_production_liters") or []
    emis_hist = histories.get("total_ghg_emissions_tco2e") or []
    milk_fig = _history_plus_projection_figure(
        title="Produção de leite — histórico e projeção",
        history=milk_hist,
        value_key="milk_production_liters",
        forecast_labels=periods,
        forecast_values=result.get("milk_predictions"),
        yaxis_title="Litros",
    )
    emis_fig = _history_plus_projection_figure(
        title="Emissões — histórico e projeção",
        history=emis_hist,
        value_key="total_ghg_emissions_tco2e",
        forecast_labels=periods,
        forecast_values=result.get("emission_predictions"),
        yaxis_title="t CO₂e",
    )
    return dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=milk_fig, config=_CHART_CONFIG, className="dashboard-chart"), md=6),
            dbc.Col(dcc.Graph(figure=emis_fig, config=_CHART_CONFIG, className="dashboard-chart"), md=6),
        ],
        className="g-3 mb-3",
    )


def empty_result_message(message: str) -> html.Div:
    return AlertBox(message, variant="info", className="small")


def _period_display(iso_or_label: str) -> str:
    text = str(iso_or_label)
    if "T" in text or len(text) >= 10 and text[4] == "-":
        try:
            import pandas as pd

            ts = pd.Timestamp(text)
            months = (
                "jan", "fev", "mar", "abr", "mai", "jun",
                "jul", "ago", "set", "out", "nov", "dez",
            )
            return f"{months[ts.month - 1]}/{ts.year}"
        except Exception:
            return text[:10]
    return text


def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    apply_chart_theme(fig, title=title)
    fig.add_annotation(
        text="Sem dados para exibir",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color=COLORS.get("text_muted", COLORS["text"]), size=14),
    )
    return fig


def _observed_plus_forecast_figure(
    *,
    title: str,
    history: list[dict[str, Any]],
    value_key: str,
    forecast_label: str,
    forecast_value: float | None,
    yaxis_title: str,
) -> go.Figure:
    labels = [_period_display(row.get("period", "")) for row in history]
    values = [row.get(value_key) for row in history]
    has_hist = any(v is not None for v in values)
    if not has_hist and forecast_value is None:
        return _empty_figure(title)

    fig = go.Figure()
    if has_hist:
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=values,
                mode="lines+markers",
                name="Observado",
                line=dict(color=COLORS["primary"], width=2.5),
                marker=dict(size=7),
            )
        )
    if forecast_value is not None:
        fig.add_trace(
            go.Scatter(
                x=[forecast_label],
                y=[forecast_value],
                mode="markers",
                name="Previsto",
                marker=dict(color=COLORS.get("warning", "#D97706"), size=12, symbol="diamond"),
            )
        )
    apply_chart_theme(fig, title=title, yaxis_title=yaxis_title, hovermode="x unified")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


def _history_plus_projection_figure(
    *,
    title: str,
    history: list[dict[str, Any]],
    value_key: str,
    forecast_labels: list[str],
    forecast_values: list[float] | None,
    yaxis_title: str,
) -> go.Figure:
    hist_labels = [_period_display(row.get("period", "")) for row in history]
    hist_values = [row.get(value_key) for row in history]
    has_hist = any(v is not None for v in hist_values)
    has_fc = bool(forecast_values) and any(v is not None for v in (forecast_values or []))
    if not has_hist and not has_fc:
        return _empty_figure(title)

    fig = go.Figure()
    if has_hist:
        fig.add_trace(
            go.Scatter(
                x=hist_labels,
                y=hist_values,
                mode="lines+markers",
                name="Histórico",
                line=dict(color=COLORS["primary"], width=2.5),
                marker=dict(size=7),
            )
        )
    if has_fc:
        # Liga o último ponto histórico ao primeiro da projeção quando possível.
        bridge_x = list(forecast_labels)
        bridge_y = list(forecast_values or [])
        if has_hist and hist_labels and hist_values and hist_values[-1] is not None:
            bridge_x = [hist_labels[-1], *bridge_x]
            bridge_y = [hist_values[-1], *bridge_y]
        fig.add_trace(
            go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines+markers",
                name="Projeção",
                line=dict(color=COLORS.get("warning", "#D97706"), width=2.5, dash="dash"),
                marker=dict(size=8, symbol="diamond"),
            )
        )
    apply_chart_theme(fig, title=title, yaxis_title=yaxis_title, hovermode="x unified")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig
