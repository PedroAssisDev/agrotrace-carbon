"""Stepper da pipeline — 11 etapas do cycle_state."""

from __future__ import annotations

from dash import html

from components.status_badges import StatusBadge
from services.cycle_state import PIPELINE_STEP_DEFS, completed_count, progress_pct, status_label


def PipelineStepper(cycle: dict) -> html.Div:
    steps_data = cycle.get("steps") or {}
    current_status = cycle.get("current_status", "PENDING")
    done = completed_count(cycle)
    total = len(PIPELINE_STEP_DEFS)
    pct = progress_pct(cycle)

    steps = []
    for i, step_def in enumerate(PIPELINE_STEP_DEFS):
        step = steps_data.get(step_def.step_id, {})
        status = step.get("status", "PENDING")
        cls = "pipeline-step"
        if status in {"DONE", "DONE_WARNINGS", "APPROVED", "ANCHORED", "VERIFIED"}:
            cls += " done"
        elif status == "RUNNING":
            cls += " active"
        elif status in {"ERROR", "DIVERGENT"}:
            cls += " error"

        steps.append(
            html.Div([
                html.Div(str(i + 1), className="step-circle"),
                html.Small(step_def.label.split(". ", 1)[-1], className="d-block pipeline-step-label"),
            ], className=cls)
        )

    return html.Div([
        html.Div([
            html.Span(f"Progresso: {done}/{total} ({pct}%)", className="me-2 text-aux"),
            StatusBadge(current_status, label=status_label(current_status)),
        ], className="mb-2"),
        html.Div([
            html.Div(className="pipeline-stepper-progress-bar", style={"width": f"{pct}%"})
        ], className="pipeline-stepper-progress"),
        html.Div(steps, className="d-flex flex-wrap justify-content-between mb-2 pipeline-steps-row"),
    ], className="pipeline-stepper-card")
