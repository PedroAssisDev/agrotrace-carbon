"""Fachada de indicadores — reexporta API pública para compatibilidade."""

from services.indicator_aggregation_service import build_dashboard_indicators
from services.indicator_chart_service import (
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_executive_temporal_section,
    build_executive_temporal_series,
)
from services.indicator_kpi_service import (
    build_dashboard_tables,
    build_section_kpis,
    generate_dashboard_insights,
    group_insights_by_severity,
)

__all__ = [
    "build_dashboard_indicators",
    "build_dashboard_chart_series",
    "build_dashboard_chart_components",
    "build_dashboard_tables",
    "build_executive_temporal_section",
    "build_executive_temporal_series",
    "build_section_kpis",
    "generate_dashboard_insights",
    "group_insights_by_severity",
]
