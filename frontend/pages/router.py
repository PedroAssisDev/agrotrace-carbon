"""Roteador de páginas — camada gerencial + auditoria técnica."""

from __future__ import annotations

from dash import html

from pages import (
    approval_review,
    dashboard,
    data_entry,
    emission_calculations,
    forecasts,
    settings,
    sustainability_indicators,
    technical_audit,
)

ROUTES = {
    "/": dashboard.layout,
    "/data-entry": data_entry.layout,
    "/calculations": emission_calculations.layout,
    "/approval": approval_review.layout,
    "/indicators": sustainability_indicators.layout,
    "/previsoes": forecasts.layout,
    "/technical-audit": technical_audit.layout,
    "/settings": settings.layout,
}

def render_page(
    pathname: str | None,
    cycle: dict | None,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
    upload_feedback: dict | None = None,
    active_audit_tab: str | None = None,
) -> html.Div:
    cycle = cycle or {}
    path = pathname or "/"

    if path == "/data-entry":
        return data_entry.layout(
            cycle, global_filter or {}, filter_options or {}, context_cycle_id, upload_feedback,
        )

    if path == "/technical-audit":
        return technical_audit.layout(
            cycle,
            global_filter or {},
            filter_options or {},
            context_cycle_id,
            active_tab=active_audit_tab or "ta-summary",
        )

    fn = ROUTES.get(path, dashboard.layout)
    return fn(cycle, global_filter or {}, filter_options or {}, context_cycle_id)
