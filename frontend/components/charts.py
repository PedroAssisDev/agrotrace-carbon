"""Gráficos Plotly."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc, html

from layout.theme import CHART_FONT, CHART_PALETTE, COLORS, EMISSION_SOURCE_COLORS
from utils.formatting import format_number

_CHART_CONFIG = {"displayModeBar": False, "responsive": True}
_CHART_HEIGHT = 340
_EXECUTIVE_CHART_HEIGHT = 380
_EXECUTIVE_CHART_MARGIN = dict(l=58, r=24, t=72, b=72)
_EXECUTIVE_PIE_HEIGHT = 440

_CHART_TITLE_SIZE = 18
_CHART_TICK_SIZE = 14
_CHART_AXIS_TITLE_SIZE = 15
_CHART_LEGEND_SIZE = 14
_CHART_HOVER_SIZE = 15

_AXIS_TITLE_FONT = dict(family=CHART_FONT["family"], size=_CHART_AXIS_TITLE_SIZE, color=COLORS["text"])
_TICK_FONT = dict(family=CHART_FONT["family"], size=_CHART_TICK_SIZE, color=COLORS["text"])
_AXIS_COLOR = COLORS["text"]
_GRID_COLOR = COLORS.get("grid", "#E5E7EB")
_ZEROLINE_COLOR = COLORS.get("zeroline", "#D1D5DB")
_PLOT_BG = COLORS.get("surface_muted", "#EEF3EF")


def _hex_with_alpha(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _title_layout(title: str) -> dict:
    return dict(
        text=f"<b>{title}</b>",
        font=dict(size=_CHART_TITLE_SIZE, family=CHART_FONT["family"], color=COLORS["text"]),
        x=0,
        xanchor="left",
        y=0.98,
        yanchor="top",
    )


def _polish_cartesian_axes(fig: go.Figure, *, tickangle: int = 0) -> go.Figure:
    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor=COLORS["border"],
        mirror=False,
        ticks="outside",
        ticklen=4,
        tickangle=tickangle,
        automargin=True,
        tickfont=_TICK_FONT,
        title_font=_AXIS_TITLE_FONT,
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=_GRID_COLOR,
        griddash="dot",
        zeroline=False,
        showline=False,
        ticks="",
        automargin=True,
        separatethousands=True,
        tickfont=_TICK_FONT,
        title_font=_AXIS_TITLE_FONT,
    )
    return fig


def apply_chart_theme(fig: go.Figure, title: str = "", **kwargs) -> go.Figure:
    layout_kwargs = dict(
        font=dict(
            family=CHART_FONT["family"],
            color=CHART_FONT["color"],
            size=CHART_FONT.get("size", 14),
        ),
        title=_title_layout(title) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=_PLOT_BG,
        margin=dict(l=58, r=24, t=72, b=60),
        height=_CHART_HEIGHT,
        colorway=CHART_PALETTE,
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border_strong"],
            font=dict(family=CHART_FONT["family"], size=_CHART_HOVER_SIZE, color=COLORS["text"]),
            align="left",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            font=dict(family=CHART_FONT["family"], size=_CHART_LEGEND_SIZE, color=COLORS["text"]),
        ),
        xaxis=dict(
            color=_AXIS_COLOR,
            gridcolor=_GRID_COLOR,
            zerolinecolor=_ZEROLINE_COLOR,
            linecolor=COLORS["border"],
            tickfont=_TICK_FONT,
            title_font=_AXIS_TITLE_FONT,
        ),
        yaxis=dict(
            color=_AXIS_COLOR,
            gridcolor=_GRID_COLOR,
            zerolinecolor=_ZEROLINE_COLOR,
            linecolor=COLORS["border"],
            tickfont=_TICK_FONT,
            title_font=_AXIS_TITLE_FONT,
        ),
    )
    yaxis_title_text = kwargs.pop("yaxis_title", None)
    if yaxis_title_text:
        kwargs["yaxis_title"] = f"<b>{yaxis_title_text}</b>"
    xaxis_title_text = kwargs.pop("xaxis_title", None)
    if xaxis_title_text:
        kwargs["xaxis_title"] = f"<b>{xaxis_title_text}</b>"
    layout_kwargs.update(kwargs)
    if layout_kwargs.get("title") is None:
        layout_kwargs.pop("title", None)
    fig.update_layout(**layout_kwargs)
    if fig.data and getattr(fig.data[0], "type", "") in {"scatter", "bar"}:
        _polish_cartesian_axes(fig)
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
        font=dict(size=15, color=COLORS["text_secondary"], family=CHART_FONT["family"]),
    )
    return fig


def _source_color(label: str, index: int = 0) -> str:
    for key, color in EMISSION_SOURCE_COLORS.items():
        if key.lower() in label.lower():
            return color
    return CHART_PALETTE[index % len(CHART_PALETTE)]


def _short_source_label(label: str) -> str:
    """Nome curto para legenda — remove sufixo de gás quando presente."""
    if " — " in label:
        return label.split(" — ", 1)[0].strip()
    return label.strip()


def _prepare_emission_pie_series(by_source: dict) -> tuple[list[str], list[float], list[str]]:
    """Ordena fontes por valor decrescente; retorna rótulos curtos, valores e rótulos completos."""
    items = sorted(
        ((str(k), float(v or 0)) for k, v in by_source.items() if v is not None and float(v or 0) > 0),
        key=lambda x: -x[1],
    )
    if not items:
        return [], [], []
    full_labels = [k for k, _ in items]
    values = [v for _, v in items]
    display_labels = [_short_source_label(k) for k in full_labels]
    return display_labels, values, full_labels


def _pie_trace(labels: list, values: list) -> go.Pie:
    colors = [_source_color(lbl, i) for i, lbl in enumerate(labels)]
    return go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=1)),
        textfont=dict(family=CHART_FONT["family"], size=_CHART_LEGEND_SIZE, color=COLORS["text"]),
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
            x=labels,
            y=values,
            mode="lines+markers",
            line=dict(color=line_color, width=2.5, shape="spline", smoothing=0.35),
            marker=dict(
                color=line_color,
                size=8,
                line=dict(color=COLORS["surface"], width=1.5),
            ),
            fill="tozeroy",
            fillcolor=_hex_with_alpha(line_color, 0.14),
            hovertemplate="<b>%{x}</b><br><b>%{y:,.2f}</b><extra></extra>",
        )])
        apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None, hovermode="x unified")
        _polish_cartesian_axes(fig, tickangle=-30 if len(labels) > 4 else 0)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def BarChart(title: str, labels: list, values: list, color: str | None = None, yaxis_title: str = "") -> dcc.Graph:
    if not labels or not values:
        fig = _empty_annotation(title)
    else:
        bar_color = color or COLORS["primary"]
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=bar_color,
                line=dict(color=_hex_with_alpha(bar_color, 0.85), width=0),
                cornerradius=5,
            ),
            hovertemplate="<b>%{x}</b><br><b>%{y:,.2f}</b><extra></extra>",
        )])
        apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None, hovermode="x unified")
        _polish_cartesian_axes(fig, tickangle=-30 if len(labels) > 4 else 0)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def PieChart(title: str, labels: list, values: list) -> dcc.Graph:
    if not labels or not values:
        fig = _empty_annotation(title)
    else:
        fig = go.Figure(data=[_pie_trace(labels, values)])
        apply_chart_theme(
            fig,
            title=title,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
                font=dict(family=CHART_FONT["family"], size=_CHART_LEGEND_SIZE, color=COLORS["text"]),
            ),
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def ExecutiveEmissionSourcePieChart(by_source: dict | None = None) -> dcc.Graph:
    """Donut executivo — legenda lateral, total central e hover detalhado."""
    by_source = by_source or {}
    display_labels, values, full_labels = _prepare_emission_pie_series(by_source)
    title = "Emissões por fonte"

    if not values:
        fig = _empty_annotation(title)
    else:
        total_kg = sum(values)
        total_t = total_kg / 1000.0
        values_t = [v / 1000.0 for v in values]
        colors = [_source_color(full, i) for i, full in enumerate(full_labels)]
        legend_labels = [
            f"{label} — {100 * value / total_kg:.1f}%".replace(".", ",")
            for label, value in zip(display_labels, values)
        ]
        pull = [0.04 if i == 0 and len(values) > 1 else 0.0 for i in range(len(values))]

        fig = go.Figure(data=[go.Pie(
            labels=legend_labels,
            values=values_t,
            hole=0.55,
            sort=False,
            direction="clockwise",
            rotation=90,
            domain=dict(x=[0.0, 0.46], y=[0.02, 0.98]),
            marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="none",
            pull=pull,
            customdata=full_labels,
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "<b>%{value:,.3f}</b> t CO₂e<br>"
                "<b>%{percent}</b><extra></extra>"
            ),
        )])
        apply_chart_theme(
            fig,
            title=title,
            height=_EXECUTIVE_PIE_HEIGHT,
            margin=dict(l=12, r=12, t=68, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=COLORS["surface"],
            showlegend=True,
            hovermode="closest",
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=0.50,
                font=dict(family=CHART_FONT["family"], size=_CHART_LEGEND_SIZE + 1, color=COLORS["text"]),
                traceorder="normal",
                itemsizing="constant",
            ),
        )
        fig.update_xaxes(visible=False, showgrid=False)
        fig.update_yaxes(visible=False, showgrid=False)
        fig.add_annotation(
            text=(
                f"<b style='font-size:22px'>{format_number(total_t, 1)}</b>"
                f"<br><span style='font-size:14px;font-weight:600;color:{COLORS['text_muted']}'>t CO₂e total</span>"
            ),
            x=0.23,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            align="center",
            font=dict(family=CHART_FONT["family"], size=22, color=COLORS["text"]),
        )

    return dcc.Graph(
        figure=fig,
        config=_CHART_CONFIG,
        className="dashboard-chart executive-emission-pie-chart",
    )


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
            bar_color = colors[i % len(colors)]
            fig.add_trace(go.Bar(
                name=name,
                x=list(categories),
                y=y_data,
                marker=dict(color=bar_color, cornerradius=4),
                hovertemplate="<b>%{x}</b><br><b>%{y:,.2f}</b><extra></extra>",
            ))
        apply_chart_theme(fig, title=title, barmode="group", hovermode="x unified")
        _polish_cartesian_axes(fig, tickangle=-25 if len(categories) > 4 else 0)
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
                marker=dict(color=_source_color(name, i), cornerradius=3),
                hovertemplate="<b>%{x}</b><br><b>%{y:,.2f}</b><extra></extra>",
            ))
        apply_chart_theme(fig, title=title, barmode="stack", hovermode="x unified")
        _polish_cartesian_axes(fig, tickangle=-25 if len(labels) > 4 else 0)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart")


def HorizontalBarChart(
    title: str,
    labels: list,
    values: list,
    *,
    color: str | None = None,
    xaxis_title: str = "",
) -> dcc.Graph | None:
    """Ranking horizontal — fontes emissoras."""
    pairs = [(l, v) for l, v in zip(labels, values) if v is not None and v > 0]
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[1])
    sorted_labels = [p[0] for p in pairs]
    sorted_values = [p[1] for p in pairs]
    bar_colors = [_source_color(lbl, i) for i, lbl in enumerate(sorted_labels)]
    fig = go.Figure(data=[go.Bar(
        y=sorted_labels,
        x=sorted_values,
        orientation="h",
        marker=dict(color=bar_colors, cornerradius=4),
        hovertemplate="<b>%{y}</b><br>%{x:,.2f}<extra></extra>",
    )])
    apply_chart_theme(fig, title=title, xaxis_title=xaxis_title or None, height=min(340, 80 + 36 * len(sorted_labels)))
    fig.update_layout(margin=dict(l=140, r=24, t=72, b=48))
    fig.update_xaxes(showgrid=True, gridcolor=_GRID_COLOR, tickfont=_TICK_FONT)
    fig.update_yaxes(tickfont=_TICK_FONT, automargin=True)
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart horizontal-bar-chart")


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


def temporal_chart_empty_card(message: str) -> html.Div:
    """Estado vazio discreto para gráficos temporais do Painel Executivo."""
    return html.Div(
        html.P(message, className="text-aux mb-0 small"),
        className="executive-temporal-empty summary-card p-3 mb-2",
    )


def ExecutiveTemporalChart(
    title: str,
    labels: list,
    values: list,
    *,
    yaxis_title: str = "",
    color: str | None = None,
    hover_template: str | None = None,
    element_id: str | None = None,
    y_tickformat: str | None = None,
) -> dcc.Graph | None:
    """Gráfico temporal de métrica única — barra (1 ponto) ou linha (≥2). Retorna None se vazio."""
    pairs = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not pairs:
        return None
    valid_labels, valid_values = zip(*pairs)
    valid_labels = list(valid_labels)
    valid_values = list(valid_values)
    chart_color = color or COLORS["primary"]
    tickangle = -32 if len(valid_labels) > 4 else 0
    hover_body = hover_template or "<b>%{y:,.2f}</b><extra></extra>"
    if "%{x}" not in hover_body:
        if "<br>" in hover_body:
            _, value_part = hover_body.split("<br>", 1)
            hover_body = f"<b>%{{x}}</b><br>{value_part}"
        else:
            hover_body = f"<b>%{{x}}</b><br>{hover_body}"

    layout_extra = dict(
        height=_EXECUTIVE_CHART_HEIGHT,
        margin=_EXECUTIVE_CHART_MARGIN,
        showlegend=False,
        hovermode="x unified",
    )
    if len(pairs) == 1:
        trace = go.Bar(
            x=valid_labels,
            y=valid_values,
            marker=dict(
                color=chart_color,
                line=dict(color=_hex_with_alpha(chart_color, 0.9), width=0),
                cornerradius=8,
            ),
            width=0.45,
            hovertemplate=hover_body,
        )
    else:
        trace = go.Scatter(
            x=valid_labels,
            y=valid_values,
            mode="lines+markers",
            line=dict(color=chart_color, width=2.8, shape="spline", smoothing=0.35),
            marker=dict(
                color=chart_color,
                size=9,
                line=dict(color=COLORS["surface"], width=2),
            ),
            fill="tozeroy",
            fillcolor=_hex_with_alpha(chart_color, 0.16),
            hovertemplate=hover_body,
        )
    fig = go.Figure(data=[trace])
    apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None, **layout_extra)
    _polish_cartesian_axes(fig, tickangle=tickangle)
    if y_tickformat:
        fig.update_yaxes(tickformat=y_tickformat)
    elif yaxis_title and "L" in yaxis_title and "CO" not in yaxis_title:
        fig.update_yaxes(tickformat=",.0f")
    elif yaxis_title and "kg CO" in yaxis_title:
        fig.update_yaxes(tickformat=",.3f")
    else:
        fig.update_yaxes(tickformat=",.2f")
    return dcc.Graph(
        id=element_id,
        figure=fig,
        config=_CHART_CONFIG,
        className="dashboard-chart executive-temporal-chart",
    )


def MultiLineTemporalChart(
    title: str,
    labels: list,
    series: dict[str, list],
    *,
    yaxis_title: str = "",
    min_points: int = 1,
) -> dcc.Graph | None:
    """Gráfico temporal com múltiplas séries (fontes emissoras ou gases).

    Clique na legenda para mostrar/ocultar curvas; duplo clique isola uma curva.
    """
    if not labels or not series:
        return None

    aligned: dict[str, list[float | None]] = {}
    for name, vals in series.items():
        row: list[float | None] = []
        for idx in range(len(labels)):
            if idx < len(vals) and vals[idx] is not None:
                try:
                    row.append(float(vals[idx]))
                except (TypeError, ValueError):
                    row.append(None)
            else:
                row.append(None)
        if any(v is not None for v in row):
            aligned[name] = row

    if not aligned:
        return None

    points_with_data = sum(
        1 for idx in range(len(labels))
        if any(aligned[name][idx] is not None for name in aligned)
    )
    if points_with_data < min_points:
        return None

    fig = go.Figure()
    for i, (name, vals) in enumerate(aligned.items()):
        color = _source_color(name, i)
        fig.add_trace(go.Scatter(
            x=labels,
            y=vals,
            mode="lines+markers",
            name=name,
            connectgaps=False,
            line=dict(color=color, width=2.2, shape="spline", smoothing=0.35),
            marker=dict(color=color, size=7, line=dict(color=COLORS["surface"], width=1.5)),
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{y:,.3f}}<extra></extra>",
        ))
    apply_chart_theme(fig, title=title, yaxis_title=yaxis_title or None, hovermode="x unified")
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(family=CHART_FONT["family"], size=_CHART_LEGEND_SIZE, color=COLORS["text"]),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
    )
    _polish_cartesian_axes(fig, tickangle=-30 if len(labels) > 4 else 0)
    fig.update_yaxes(tickformat=",.3f")
    return dcc.Graph(figure=fig, config=_CHART_CONFIG, className="dashboard-chart multi-line-temporal-chart")
