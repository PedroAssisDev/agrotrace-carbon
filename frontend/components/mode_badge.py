"""Badge de modo de integração (real/mock) e governança de dados."""

from __future__ import annotations

from dash import html

from utils.global_filter import DATA_MODE_OPTIONS


def ModeBadge(mode: str | None) -> html.Span:
    if mode == "real":
        return html.Span("Dados reais", className="badge-status badge-status-dados-reais me-1")
    if mode == "mock":
        return html.Span("Fallback mock", className="badge-status badge-status-fallback-mock me-1")
    return html.Span("Pendente", className="badge-status badge-status-pendente me-1")


def DataModeBadge(mode: str | None) -> html.Span:
    """Badge de governança: official_only | include_preliminary | all."""
    labels = DATA_MODE_OPTIONS
    key = mode if mode in labels else "include_preliminary"
    css = {
        "official_only": "badge-status-dados-reais",
        "include_preliminary": "badge-status-pendente",
        "all": "badge-status-dados-reais",
    }.get(key, "badge-status-pendente")
    return html.Span(labels[key], className=f"badge-status {css} me-1")
