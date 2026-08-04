"""Card de etapa do wizard de Ciclos de Emissão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox
from components.mode_badge import ModeBadge
from components.status_badges import StatusBadge
from services.cycle_state import STEP_BY_ID, status_label


def StepCard(
    step_id: str,
    cycle: dict,
    *,
    children: html.Div | list | None = None,
    show_run: bool = True,
) -> dbc.Card:
    step_def = STEP_BY_ID.get(step_id)
    step = (cycle.get("steps") or {}).get(step_id, {})
    status = step.get("status", "PENDING")
    mode = step.get("mode")
    summary = step.get("summary")
    errors = [e for e in cycle.get("errors", []) if e.get("step") == step_id]
    warnings = [w for w in cycle.get("warnings", []) if w.get("step") == step_id]

    header = [
        html.H5(step_def.label if step_def else step_id, className="section-title mb-1"),
        html.P(step_def.description if step_def else "", className="text-aux mb-2"),
        StatusBadge(status, label=status_label(status)),
        ModeBadge(mode),
    ]

    body = [html.Div(header, className="d-flex flex-wrap align-items-center gap-2 mb-2")]
    if summary:
        body.append(html.P(summary, className="mb-2"))
    for err in errors:
        body.append(AlertBox(err.get("message", ""), variant="danger", className="py-1 small"))
    for warn in warnings:
        body.append(AlertBox(warn.get("message", ""), variant="warning", className="py-1 small"))
    if children:
        body.append(html.Div(children, className="mt-2"))
    if show_run:
        body.append(html.Div([
            dbc.Button(
                "Executar etapa",
                id={"type": "btn-wizard-step", "step": step_id},
                color="primary",
                size="sm",
                className="mt-2 me-2 btn-agro-primary",
            ),
            dbc.Button(
                "Ver detalhes",
                id={"type": "btn-wizard-detail", "step": step_id},
                color="secondary",
                outline=True,
                size="sm",
                className="mt-2 btn-agro-secondary",
            ),
        ]))

    return dbc.Card(dbc.CardBody(body), className="agro-card mb-3")
