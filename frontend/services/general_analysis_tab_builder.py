"""Montagem sob demanda das abas da Análise Geral."""

from __future__ import annotations

from dash import html

from components.conditional_widgets import ConditionalChartSection
from components.dashboard_layout_helpers import section_body
from components.general_analysis.governance import GovernanceSection
from components.general_analysis.overview import OverviewSection
from components.general_analysis.tables import SupportTablesSection
from services.dashboard_service import (
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_section_kpis,
)
from services.general_analysis_service import (
    build_production_management_kpis,
    filter_nonempty_kpis,
)


def filter_section_kpis(indicators: dict, section_key: str) -> list[dict]:
    prod = indicators.get("productivity") or {}
    kpis = build_section_kpis(
        indicators,
        section_key,
        include_traceability=(section_key in ("emissions", "sustainability")),
        productivity_section=prod,
    )
    return filter_nonempty_kpis(kpis)


def build_general_analysis_tab_content(
    tab_id: str,
    indicators: dict,
    tables: dict,
    work_cycles: list[dict],
) -> html.Div:
    """Renderiza somente a aba ativa (gráficos Plotly gerados sob demanda)."""
    chart_series = build_dashboard_chart_components(
        build_dashboard_chart_series(indicators, work_cycles),
        for_general_analysis=True,
    )

    if tab_id == "overview":
        body = OverviewSection(indicators)
    elif tab_id == "production":
        body = section_body(
            build_production_management_kpis(indicators),
            (chart_series.get("productivity") or []) + (chart_series.get("management") or []),
            SupportTablesSection(tables, keys=["cycles_analyzed"]),
        )
    elif tab_id == "emissions":
        body = section_body(
            filter_section_kpis(indicators, "emissions"),
            chart_series.get("emissions") or [],
            SupportTablesSection(tables, keys=["ranking_sources", "period_indicators"]),
        )
    elif tab_id == "sustainability":
        sus_extra = html.Div([
            html.P(
                "Quanto menor o valor de kg CO₂e/L, melhor o desempenho ambiental por litro produzido.",
                className="text-aux small mb-2",
            ),
            SupportTablesSection(tables, keys=["period_indicators"]),
        ])
        body = section_body(
            filter_section_kpis(indicators, "sustainability"),
            chart_series.get("sustainability") or [],
            sus_extra,
        )
    elif tab_id == "quality":
        body = section_body(
            filter_section_kpis(indicators, "data_quality"),
            chart_series.get("data_quality") or [],
            SupportTablesSection(tables, keys=["traceability"]),
        )
    elif tab_id == "governance":
        body = [
            *GovernanceSection(indicators),
            ConditionalChartSection(
                (chart_series.get("pipeline") or []) + (chart_series.get("auditability") or [])
            ),
            SupportTablesSection(tables, keys=["cycles_analyzed"]),
        ]
    else:
        body = OverviewSection(indicators)

    if isinstance(body, list):
        return html.Div(body, className="dashboard-tab-panel")
    return html.Div(body, className="dashboard-tab-panel")
