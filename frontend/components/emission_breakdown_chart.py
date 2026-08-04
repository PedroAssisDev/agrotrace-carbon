"""Gráfico unificado de emissões por fonte."""

from __future__ import annotations

from dash import html

from components.charts import BarChart, PieChart


def EmissionBreakdownChart(sources: list[dict], *, chart_type: str = "bar") -> html.Div | BarChart:
    if not sources:
        return html.Div()
    labels = [s.get("fonte", s.get("source", "—")) for s in sources]
    values = [s.get("co2e_kg", s.get("value", 0)) for s in sources]
    if chart_type == "pie":
        return PieChart("Emissões por fonte (kg CO₂e)", labels, values)
    return BarChart("Emissões por fonte (kg CO₂e)", labels, values)
