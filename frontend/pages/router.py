"""Roteador de páginas — camada gerencial + auditoria técnica."""

from __future__ import annotations

from dash import dcc, html

from pages import (
    approval_review,
    dashboard,
    data_entry,
    emission_calculations,
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
    "/technical-audit": technical_audit.layout,
    "/settings": settings.layout,
}

LEGACY_REDIRECTS = {
    "/farm": "/",
    "/farms": "/",
    "/emission-cycles": "/technical-audit",
    "/data": "/technical-audit",
    "/raw-data": "/technical-audit",
    "/wrappers": "/technical-audit",
    "/normalized-data": "/technical-audit",
    "/ontology": "/technical-audit",
    "/semantic-validation": "/technical-audit",
    "/provenance": "/technical-audit",
    "/blockchain": "/technical-audit",
    "/immutability": "/technical-audit",
    "/approvals": "/approval",
    "/final-publication": "/approval",
    "/dashboard": "/",
    "/reports": "/indicators",
}


def render_page(
    pathname: str | None,
    cycle: dict | None,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    cycle = cycle or {}
    path = pathname or "/"

    if path in LEGACY_REDIRECTS:
        target = LEGACY_REDIRECTS[path]
        if target != path:
            return html.Div([
                dcc.Location(id="legacy-redirect", pathname=target, refresh=True),
                html.P(f"Redirecionando para {target}…", className="text-muted p-4"),
            ])

    fn = ROUTES.get(path, dashboard.layout)
    return fn(cycle, global_filter or {}, filter_options or {}, context_cycle_id)
