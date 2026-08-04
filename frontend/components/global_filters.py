"""Componente global de filtros analíticos (fazenda + período de análise) para o navbar."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils.global_filter import (
    DATA_MODE_OPTIONS,
    DEFAULT_GLOBAL_FILTER,
    GRANULARITY_LABELS,
    VIEW_GRANULARITY_OPTIONS,
    format_filter_badge,
    format_period_label,
    format_status_badge_label,
)
from utils.temporal_model import CALC_BASE_LABELS


def _property_options(catalog: list[dict]) -> list[dict]:
    opts = []
    for p in catalog or []:
        loc = ""
        if p.get("municipality") or p.get("state"):
            loc = f" — {p.get('municipality', '')}/{p.get('state', '')}".rstrip("/")
        opts.append({"label": f"{p.get('name', p['property_id'])}{loc}", "value": p["property_id"]})
    return opts


def _aggregated_status_label(status: str | None) -> str:
    labels = {
        "approved": "Aprovado",
        "partial_pending": "Parcial / Pendente",
        "partial": "Parcial",
        "pending_approval": "Pendente",
        "published": "Publicado",
        "rejected": "Reprovado",
    }
    return labels.get(status or "", status or "—")


def GlobalFilters(
    filter_options: dict | None = None,
    global_filter: dict | None = None,
) -> html.Div:
    """Filtro global compacto no topo do sistema."""
    gf = global_filter or DEFAULT_GLOBAL_FILTER
    options = filter_options or {}
    properties = options.get("properties") or []
    analysis_periods = options.get("analysis_periods") or []
    show_analysis_period = len(analysis_periods) > 1

    period_display = gf.get("period_display_label") or format_period_label(gf.get("period") or "")
    calc_base = gf.get("calculation_base_granularity") or gf.get("granularity")
    calc_label = CALC_BASE_LABELS.get(calc_base or "", GRANULARITY_LABELS.get(calc_base or "", "—"))
    status_label = format_status_badge_label(gf)
    view_val = gf.get("view_granularity") or "auto"
    data_mode_val = gf.get("data_mode") or "include_preliminary"
    agg_status = gf.get("aggregated_approval_status")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Small("Propriedade", className="gf-label"),
                            dcc.Dropdown(
                                id="gf-property-dropdown",
                                options=_property_options(properties),
                                value=gf.get("farm_id"),
                                placeholder="Selecione uma fazenda…",
                                className="gf-property-dropdown",
                            ),
                        ],
                        className="gf-field",
                    ),
                    html.Div(
                        [
                            html.Small("Período de", className="gf-label"),
                            dcc.Dropdown(
                                id="gf-analysis-start",
                                options=analysis_periods,
                                value=gf.get("analysis_period_start"),
                                placeholder="Início…",
                                clearable=False,
                                className="gf-property-dropdown",
                            ),
                        ],
                        id="gf-analysis-start-field",
                        className="gf-field",
                        style={"display": "block" if show_analysis_period else "none"},
                    ),
                    html.Div(
                        [
                            html.Small("até", className="gf-label"),
                            dcc.Dropdown(
                                id="gf-analysis-end",
                                options=analysis_periods,
                                value=gf.get("analysis_period_end"),
                                placeholder="Fim…",
                                clearable=False,
                                className="gf-property-dropdown",
                            ),
                        ],
                        id="gf-analysis-end-field",
                        className="gf-field",
                        style={"display": "block" if show_analysis_period else "none"},
                    ),
                    html.Div(
                        [
                            html.Small("Visualização", className="gf-label"),
                            dcc.Dropdown(
                                id="gf-view-granularity",
                                options=[{"label": v, "value": k} for k, v in VIEW_GRANULARITY_OPTIONS.items()],
                                value=view_val,
                                clearable=False,
                                className="gf-property-dropdown",
                            ),
                        ],
                        className="gf-field",
                    ),
                    html.Div(
                        [
                            html.Small("Dados", className="gf-label"),
                            dcc.Dropdown(
                                id="gf-data-mode",
                                options=[{"label": v, "value": k} for k, v in DATA_MODE_OPTIONS.items()],
                                value=data_mode_val,
                                clearable=False,
                                className="gf-property-dropdown",
                            ),
                        ],
                        className="gf-field",
                    ),
                    html.Span(
                        f"Período: {period_display}",
                        id="gf-period-badge",
                        className="badge-status badge-status-dados-reais mb-1",
                    ),
                    html.Span(
                        f"Cálculo: {calc_label}",
                        id="gf-granularity-badge",
                        className="badge-status badge-status-dados-reais mb-1 ms-1",
                    ),
                    html.Span(
                        f"Status: {status_label}",
                        id="gf-status-badge",
                        className="badge-status badge-status-pendente mb-1 ms-1",
                    ),
                    html.Span(
                        f"Agregado: {_aggregated_status_label(agg_status)}",
                        id="gf-aggregated-badge",
                        className="badge-status badge-status-pendente mb-1 ms-1",
                        style={"display": "inline" if agg_status else "none"},
                    ),
                    dbc.Button(
                        "Limpar",
                        id="btn-gf-clear",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="ms-1 mb-1",
                    ),
                ],
                className="d-flex flex-wrap align-items-end gf-row",
            ),
            html.Span(
                format_filter_badge(gf, options),
                id="gf-filter-badge",
                className="badge-status badge-status-dados-reais mt-1",
            ),
        ],
        className="global-filters",
    )
