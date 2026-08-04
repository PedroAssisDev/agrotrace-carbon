"""Insights agrupados por severidade."""

from __future__ import annotations

from dash import html

from components.cards import AlertBox, SectionHeader
from services.indicator_kpi_service import SEVERITY_GROUPS, group_insights_by_severity


def InsightsSection(insights: list[dict]) -> list:
    if not insights:
        from components.empty_state import EmptyState
        return [
            SectionHeader("Insights e alertas"),
            EmptyState(
                "Nenhum insight disponível",
                "Os insights são gerados automaticamente a partir dos indicadores do período.",
                icon="fas fa-lightbulb",
            ),
        ]

    groups = group_insights_by_severity(insights)
    order = ["critical", "warning", "info", "success"]
    body: list = [SectionHeader("Insights e alertas", subtitle="Orientações para decisão gerencial.")]

    for sev in order:
        items = groups.get(sev) or []
        if not items:
            continue
        label = SEVERITY_GROUPS.get(sev, sev)
        body.append(html.H6(label, className="insight-group-title mt-3 mb-2"))
        for ins in items:
            variant_map = {"critical": "danger", "warning": "warning", "info": "info", "success": "success"}
            body.append(AlertBox(
                ins.get("message", ""),
                variant=variant_map.get(sev, "info"),
                title=ins.get("title", ""),
                className="small insight-alert-item",
            ))
    return body
