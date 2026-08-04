"""Facade do Painel Geral — reexporta indicator_service para compatibilidade."""

from services.indicator_service import (  # noqa: F401
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_dashboard_indicators,
    build_dashboard_tables,
    build_section_kpis,
    generate_dashboard_insights,
)
