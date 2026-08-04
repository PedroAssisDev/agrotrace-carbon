"""Widgets condicionais — só renderizam com dados suficientes."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import CompactMetricCard, KpiGrid
from services.data_availability import resolve_visible_widgets
from utils.formatting import format_co2e, format_intensity, format_number


def _format_kpi_value(spec_meta: dict) -> str:
    val = spec_meta.get("value")
    if val is None or val == "—" or val == "N/A":
        return "—"
    title = (spec_meta.get("title") or "").lower()
    if "co₂e" in title or "co2e" in title:
        return format_co2e(val)
    if "intensidade" in title or "kg co" in title:
        return format_intensity(val)
    if isinstance(val, (int, float)):
        return format_number(val)
    return str(val)


def ConditionalKpiGrid(
    screen: str,
    *,
    cycle: dict,
    indicators: dict,
    property_profile: dict | None = None,
    col_md: int = 3,
    max_items: int | None = None,
) -> html.Div:
    visible = resolve_visible_widgets(
        screen, cycle=cycle, indicators=indicators, property_profile=property_profile,
    )
    if max_items:
        visible = visible[:max_items]
    if not visible:
        return html.Div()
    metrics = []
    for _spec, meta in visible:
        metrics.append({
            "title": meta["title"],
            "value": _format_kpi_value(meta),
            "icon": meta.get("icon", "fas fa-chart-bar"),
            "color": meta.get("color", "success"),
        })
    return KpiGrid(metrics, col_md=col_md)


def ConditionalChartSection(charts: list, *, min_charts: int = 1) -> html.Div:
    """Oculta seção de gráficos se lista vazia ou só placeholders."""
    valid = [c for c in charts if c is not None]
    if len(valid) < min_charts:
        return html.Div()
    return html.Div(valid, className="conditional-chart-section mb-3")


def DataAvailabilityGuard(visible: bool, children, *, fallback=None) -> html.Div:
    if not visible:
        return html.Div(fallback or [])
    return html.Div(children)
