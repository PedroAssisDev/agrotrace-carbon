"""Badge de origem real/mock/mixed/fallback."""

from __future__ import annotations

from dash import html

from components.mode_badge import IntegrationModeBadge


def MockSourceBadge(mode: str | None, *, label: str | None = None) -> html.Span:
    """Wrapper sobre IntegrationModeBadge para seções de auditoria."""
    badge = IntegrationModeBadge(mode)
    if label:
        return html.Span([
            badge,
            html.Small(f" {label}", className="text-muted ms-1"),
        ], className="d-inline-flex align-items-center")
    return badge
