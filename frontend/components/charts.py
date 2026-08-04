"""Gráficos Plotly."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc

from layout.theme import CHART_FONT, CHART_PALETTE, COLORS, EMISSION_SOURCE_COLORS

_CHART_CONFIG = {"displayModeBar": False}
_CHART_HEIGHT = 320

_AXIS_TITLE_FONT = dict(family=CHART_FONT["family"], size=13, color=COLORS["text_secondary"])
_HOVER_FONT = dict(family=CHART_FONT["family"], size=12, color=COLORS["text"])
_AXIS_COLOR = COLORS["text_secondary"]
_GRID_COLOR = COLORS.get("grid", "#E5E7EB")
_ZEROLINE_COLOR = COLORS.get("zeroline", "#D1D5DB")


def apply_chart_theme(fig: go.Figure, title: str = "", **kwargs) -> go.Figure:
    tick_font = dict(family=CHART_FONT["family"], size=12, color=_AXIS_COLOR)
    layout_kwargs = dict(
        font=dict(
            family=CHART_FONT["family"],
            color=CHART_FONT["color"],
            size=CHART_FONT.get("size", 13),
        ),
        title=dict(
            text=title,
            font=dict(size=17, family=CHART_FONT["family"], color=COLORS["text"]),
        ) if title else None,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=50, r=30, t=60, b=50),
        height=_CHART_HEIGHT,
        colorway=CHART_PALETTE,
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
            font=_HOVER_FONT,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            font=dict(family=CHART_FONT["family"], size=12, color=COLORS["text"]),
        ),
        xaxis=dict(
            color=_AXIS_COLOR,
            gridcolor=_GRID_COLOR,
            zerolinecolor=_ZEROLINE_COLOR,
            linecolor=COLORS["border"],
            tickfont=tick_font,
            title_font=_AXIS_TITLE_FONT,
        ),
        yaxis=dict(
            color=_AXIS_COLOR,
            gridcolor=_GRID_COLOR,
            zerolinecolor=_ZEROLINE_COLOR,
            linecolor=COLORS["border"],
            tickfont=tick_font,
            title_font=_AXIS_TITLE_FONT,
        ),
    )
    layout_kwargs.update(kwargs)
    if layout_kwargs.get("title") is None:
        layout_kwargs.pop("title", None)
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(
        tickfont=tick_font,
        title_font=dict(family=CHART_FONT["family"], size=13, color=COLORS["text"]),
    )
    fig.update_yaxes(
        tickfont=tick_font,
        title_font=dict(family=CHART_FONT["family"], size=13, color=COLORS["text"]),
    )
    return fig


def _as_y_list(vals) -> list:
    """Plotly exige sequência em y; aceita escalar (ex.: breakdown agregado)."""
    if vals is None:
        return []
    if isinstance(vals, (str, bytes)):
        return []
    if isinstance(vals, (list, tuple)):
        return [float(v) if v is not None else 0.0 for v in vals]
    try:
        import numpy as np
        if isinstance(vals, np.ndarray):
            flat = vals.flatten().tolist()
            return [float(v) if v is not None else 0.0 for v in flat]
        if isinstance(vals, np.generic):
            return [float(vals.item())]
    except ImportError:
        pass
    try:
        return [float(vals)]
    except (TypeError, ValueError):
        return []


def _empty_annotation(title: str) -> go.Figure:
    fig = go.Figure()
    apply_chart_theme(fig, title=title)
    fig.add_annotation(
        text="Dados não disponíveis",
        xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=COLORS["text_secondary"], family=CHART_FONT["family"]),
    )
    return fig


def _source_color(label: str, index: int = 0) -> str:
    for key, color in EMISSION_SOURCE_COLORS.items():
        if key.lower() in label.lower():
            return color
    return CHART_PALETTE[index % len(CHART_PALETTE)]


def _pie_trace(labels: list, values: list) -> go.Pie:
    colors = [_source_color(lbl, i) for i, lbl in enumerate(labels)]
    return go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=1)),
        textfont=dict(family=CHART_FONT["family"], size=12, color=COLORS["text"]),
    )


def TemporalLineChart(
    title: str,
    labels: list,
    values: list,
    yaxis_title: str = "",
    color: str | None = None,
    min_points: int = 2,
) -> dcc.Graph | None:
    """Gráfico de linha temporal — omitido se houver menos de min_points."""
    pairs = [(l, v) for l, v in zip(labels, values) if v is not None]
    if len(pairs) < min_points:
        return None
    valid_labels, valid_values = zip(*pairs)
    return LineChart(title, list(valid_labels), list(valid_values), yaxis_title=yaxis_title, color=color)


def LineChart(title: str, labels: list, values: list, yaxis_title: str = "", color: str | None = None) -> dcc.Graph:
    if not labels or not values:
        fig = _empty_annotation(title)
    else:
        line_color = color or COLORS["primary"]
        fig = go.Figure(data=[go.Scatter(
            x=labels, y=values, mode="lines+markers",
            line=dict(color=line_color, width=2),
            marker=dict(color=line_color),
        )])
        apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def BarChart(title: str, labels: list, values: list, color: str | None = None, yaxis_title: str = "") -> dcc.Graph:
    if not labels or not values:
        fig = _empty_annotation(title)
    else:
        bar_color = color or COLORS["primary"]
        fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=bar_color)])
        apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def PieChart(title: str, labels: list, values: list) -> dcc.Graph:
    if not labels or not values:
        fig = _empty_annotation(title)
    else:
        fig = go.Figure(data=[_pie_trace(labels, values)])
        apply_chart_theme(fig, title=title)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def GroupedBarChart(title: str, categories: list, series: dict[str, list]) -> dcc.Graph:
    if not categories or not series:
        fig = _empty_annotation(title)
    else:
        fig = go.Figure()
        colors = [COLORS["info"], COLORS["text_secondary"]]
        for i, (name, vals) in enumerate(series.items()):
            y_data = _as_y_list(vals)
            if not y_data:
                continue
            fig.add_trace(go.Bar(name=name, x=list(categories), y=y_data, marker_color=colors[i % len(colors)]))
        apply_chart_theme(fig, title=title, barmode="group")
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def StackedBarChart(title: str, labels: list, series: dict[str, list]) -> dcc.Graph:
    if not labels or not series:
        fig = _empty_annotation(title)
    else:
        fig = go.Figure()
        for i, (name, vals) in enumerate(series.items()):
            y_data = _as_y_list(vals)
            if not y_data:
                continue
            fig.add_trace(go.Bar(
                name=name, x=list(labels), y=y_data,
                marker_color=_source_color(name, i),
            ))
        apply_chart_theme(fig, title=title, barmode="stack")
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def EmissionChart(by_source: dict | None = None, chart_type: str = "bar") -> dcc.Graph:
    by_source = by_source or {}
    labels = list(by_source.keys())
    values = list(by_source.values())
    if chart_type == "pie":
        return PieChart("Emissões por fonte (kg CO₂e)", labels, values)
    if chart_type == "line":
        return LineChart("Emissões por fonte (kg CO₂e)", labels, values)
    return BarChart("Emissões por fonte (kg CO₂e)", labels, values)


def StatusDistributionChart(status_counts: dict) -> dcc.Graph:
    return BarChart("Status dos ciclos", list(status_counts.keys()), list(status_counts.values()), color=COLORS["info"])


def IntensityTrendChart(months: list, values: list) -> dcc.Graph:
    return LineChart("Intensidade kg CO₂e/L", months, values, yaxis_title="kg CO₂e/L", color=COLORS["warning"])
