"""Visualizador de payload JSON."""

from __future__ import annotations

import json

from dash import html

from components.empty_state import EmptyState


def PayloadViewer(data: dict | list | None, title: str = "Payload", *, light: bool = True) -> html.Div:
    if data is None:
        return html.Div(
            EmptyState("Sem payload", "Nenhum payload disponível para este evento.", icon="fas fa-code"),
            className="empty-state-container py-2",
        )
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    pre_class = "payload-viewer payload-viewer--light" if light else "payload-viewer"
    return html.Div([
        html.Div(title, className="payload-viewer-header"),
        html.Pre(text, className=pre_class),
    ])
