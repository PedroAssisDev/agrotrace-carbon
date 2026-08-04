"""Stepper estendido — 18 etapas visuais + gate blockchain."""

from __future__ import annotations

from dash import html

from components.status_badges import StatusBadge
from services.cycle_state import status_label
from services.pipeline_display import BLOCKCHAIN_GATE_AFTER, DISPLAY_PIPELINE_STEPS, display_status_for_step


def ExtendedPipelineStepper(cycle: dict) -> html.Div:
    steps = []
    for ds in DISPLAY_PIPELINE_STEPS:
        status = display_status_for_step(cycle, ds)
        cls = "pipeline-step"
        if status in {"DONE", "DONE_WARNINGS", "APPROVED", "ANCHORED", "VERIFIED"}:
            cls += " done"
        elif status == "RUNNING":
            cls += " active"
        elif status in {"ERROR", "DIVERGENT", "REJECTED"}:
            cls += " error"
        if ds.blockchain_zone:
            cls += " blockchain-zone"

        steps.append(
            html.Div([
                html.Div(str(ds.step_num), className="step-circle"),
                html.Small(ds.label, className="d-block pipeline-step-label"),
                html.Small(ds.service, className="pipeline-step-service"),
            ], className=cls, title=", ".join(ds.canonical_events))
        )

        if ds.step_num == BLOCKCHAIN_GATE_AFTER:
            steps.append(html.Div(
                "Blockchain liberado somente após versão final aprovada/publicada",
                className="pipeline-blockchain-gate",
            ))

    current = cycle.get("current_status", "PENDING")
    return html.Div([
        html.Div([
            html.Strong("Pipeline completo (18 etapas)"),
            html.Span(StatusBadge(current, label=status_label(current)), className="ms-2"),
        ], className="mb-2"),
        html.Div(steps, className="pipeline-steps-row pipeline-steps-row--extended"),
    ], className="pipeline-stepper-card pipeline-stepper-card--extended")
