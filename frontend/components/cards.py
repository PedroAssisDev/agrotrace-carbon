"""Cards executivos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.mode_badge import DataModeBadge, ModeBadge
from utils.constants import ICON_COLOR_MAP, resolve_kpi_icon
from utils.formatting import format_co2e, format_intensity, format_number

_INSIGHT_VARIANT = {
    "critical": "danger",
    "warning": "warning",
    "success": "success",
    "info": "info",
}

_ALERT_CLASS = {
    "info": "alert-info-custom",
    "warning": "alert-warning-custom",
    "danger": "alert-danger-custom",
    "success": "alert-success-custom",
    "pending": "alert-pending-custom",
    "secondary": "alert-info-custom",
}

_ALERT_ICONS = {
    "info": "fas fa-info-circle",
    "warning": "fas fa-exclamation-triangle",
    "danger": "fas fa-times-circle",
    "success": "fas fa-check-circle",
    "pending": "fas fa-clock",
    "secondary": "fas fa-info-circle",
}


def AlertBox(
    message: str,
    *,
    variant: str = "info",
    title: str | None = None,
    className: str = "",
) -> html.Div:
    """Alerta com fundo claro, texto escuro e ícone semântico."""
    cls = _ALERT_CLASS.get(variant, "alert-info-custom")
    icon = _ALERT_ICONS.get(variant, "fas fa-info-circle")
    body: list = []
    if title:
        body.append(html.Strong(title, className="d-block mb-1"))
    body.append(html.Span(message))
    extra = f" {className}" if className else ""
    return html.Div(
        [
            html.I(className=f"{icon} alert-box-icon", **{"aria-hidden": "true"}),
            html.Div(body, className="alert-box-body"),
        ],
        className=f"{cls} alert-box mb-2{extra}",
    )


def _icon_wrap(icon: str, color: str, *, large: bool = False) -> html.Div:
    icon = resolve_kpi_icon(icon)
    wrap_tone = ICON_COLOR_MAP.get(color, "green")
    size_class = "metric-icon-wrap--lg" if large else ""
    return html.Div(
        html.I(className=icon),
        className=f"metric-icon-wrap metric-icon-wrap--{wrap_tone} {size_class}".strip(),
    )


def MetricCard(title: str, value: str, subtitle: str = "", icon: str = "fas fa-chart-bar", color: str = "success") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                _icon_wrap(icon, color, large=True),
                html.Div([
                    html.Div(title, className="card-title mb-1"),
                    html.Div(value, className="metric-value mb-0"),
                    html.Small(subtitle, className="text-aux") if subtitle else None,
                ], className="ms-3"),
            ], className="d-flex align-items-center"),
        ]),
        className="metric-card mb-3",
    )


def CalculationResultCard(calculation: dict) -> dbc.Card:
    if not calculation:
        return dbc.Card(dbc.CardBody("Nenhum cálculo disponível."), className="agro-card mb-3")
    return dbc.Card([
        dbc.CardHeader("Resultado Preliminar de Emissões", className="card-title"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(MetricCard("CH4 entérico", format_number(calculation.get("ch4_enteric_kg", 0)) + " kg", icon="fas fa-wind", color="info"), md=3),
                dbc.Col(MetricCard("CH4 dejetos", format_number(calculation.get("ch4_manure_kg", 0)) + " kg", icon="fas fa-recycle", color="info"), md=3),
                dbc.Col(MetricCard("N2O fertilizantes", format_number(calculation.get("n2o_fertilizer_kg", 0)) + " kg", icon="fas fa-seedling", color="warning"), md=3),
                dbc.Col(MetricCard("CO2 energia", format_number(calculation.get("co2_energy_kg", 0)) + " kg", icon="fas fa-bolt", color="secondary"), md=3),
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col(MetricCard("Total CO2e", format_co2e(calculation.get("co2e_total_kg", 0)), icon="fas fa-cloud", color="danger"), md=4),
                dbc.Col(MetricCard("Intensidade", format_intensity(calculation.get("co2e_intensity_per_milk_liter", 0)), icon="fas fa-tint", color="primary"), md=4),
                dbc.Col(MetricCard("Por animal", format_co2e(calculation.get("co2e_per_animal", 0)), icon="fas fa-paw", color="success"), md=4),
            ]),
            html.Small(f"Fonte: {calculation.get('source', '—')} | Metodologia: {calculation.get('methodology', '—')}", className="text-aux"),
        ]),
    ], className="agro-card mb-3")


def SectionHeader(title: str, subtitle: str | None = None, badge=None) -> html.Div:
    children: list = [html.H5(title, className="section-title mb-0")]
    if badge is not None:
        children.append(html.Span(badge, className="ms-2"))
    block = [html.Div(children, className="d-flex align-items-center flex-wrap")]
    if subtitle:
        block.append(html.Small(subtitle, className="text-aux"))
    return html.Div(block, className="dashboard-section-header mb-2")


def CompactMetricCard(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "fas fa-chart-bar",
    color: str = "success",
) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                _icon_wrap(icon, color),
                html.Div([
                    html.Small(title, className="card-title d-block"),
                    html.Strong(value, className="metric-value d-block"),
                    html.Small(subtitle, className="text-aux") if subtitle else None,
                ], className="ms-2 flex-grow-1"),
            ], className="d-flex align-items-start"),
        ]),
        className="metric-card compact-metric-card h-100",
    )


def KpiGrid(metrics: list[dict], col_md: int = 3) -> dbc.Row:
    cols = []
    for m in metrics:
        cols.append(dbc.Col(
            CompactMetricCard(
                m.get("title") or m.get("label", "—"),
                str(m.get("value", "—")),
                subtitle=str(m.get("subtitle", "")),
                icon=m.get("icon", "fas fa-chart-bar"),
                color=m.get("color", "success"),
            ),
            md=col_md,
            className="mb-2",
        ))
    return dbc.Row(cols, className="dashboard-kpi-row g-3")


def InsightAlert(insight: dict) -> html.Div:
    severity = insight.get("severity", "info")
    variant = _INSIGHT_VARIANT.get(severity, "info")
    return AlertBox(
        insight.get("message", ""),
        variant=variant,
        title=insight.get("title", ""),
        className="insight-alert",
    )


__all__ = [
    "MetricCard",
    "CalculationResultCard",
    "SectionHeader",
    "CompactMetricCard",
    "KpiGrid",
    "InsightAlert",
    "AlertBox",
    "DataModeBadge",
    "ModeBadge",
]
