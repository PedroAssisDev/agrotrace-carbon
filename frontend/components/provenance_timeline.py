"""Timeline de proveniência."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.status_badges import StatusBadge
from components.payload_viewer import PayloadViewer


def ProvenanceTimeline(events: list[dict]) -> html.Div:
    if not events:
        return html.Div("Nenhum evento de proveniência registrado.", className="empty-state")

    items = []
    for evt in events:
        failed = "FAILED" in str(evt.get("event_type", ""))
        items.append(
            html.Div([
                html.Div([
                    html.Strong(evt.get("event_type", "—")),
                    StatusBadge(evt.get("status", "processed")),
                ], className="d-flex justify-content-between"),
                html.Small(f"{evt.get('created_at', '—')} | {evt.get('actor', evt.get('source_service', '—'))}", className="text-muted"),
                html.P(evt.get("description", ""), className="mb-1 small"),
                html.Details([
                    html.Summary("Payload"),
                    PayloadViewer(evt.get("payload_json", evt.get("payload", {}))),
                ]),
            ], className=f"timeline-event{' failed' if failed else ''}")
        )
    return html.Div(items)
