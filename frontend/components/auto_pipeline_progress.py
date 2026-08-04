"""Banner de progresso da pipeline automática pós-upload."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from services.cycle_state import AUTO_PIPELINE_PHASES, is_step_done


def AutoPipelineProgressBanner(cycle: dict | None) -> html.Div | None:
    if not cycle or not cycle.get("cycle_id"):
        return None

    progress = cycle.get("pipeline_progress") or {}
    current_phase = progress.get("phase")
    current_status = cycle.get("current_status", "")

    items: list = []
    for phase_key, label, step_id in AUTO_PIPELINE_PHASES:
        cls = "auto-pipeline-phase"
        if is_step_done(cycle, step_id) or (
            step_id == "approval" and current_status in {"AWAITING_HUMAN_APPROVAL", "CALCULATION_APPROVED", "VERIFIED"}
        ):
            cls += " auto-pipeline-phase--done"
        elif phase_key == current_phase:
            cls += " auto-pipeline-phase--active"
        elif (cycle.get("steps") or {}).get(step_id, {}).get("status") == "ERROR":
            cls += " auto-pipeline-phase--error"
        items.append(html.Li(label, className=cls))

    banner_variant = "success" if current_status == "AWAITING_HUMAN_APPROVAL" else "info"
    if current_status in {"FAILED", "REJECTED", "CORRECTION_REQUESTED"}:
        banner_variant = "danger"
    elif current_status in {"VERIFIED", "PROVENANCE_CHAIN_VERIFIED"}:
        banner_variant = "success"

    title = progress.get("label") or "Pipeline automática"
    if current_status == "AWAITING_HUMAN_APPROVAL":
        title = "Resultado preliminar gerado — aguardando aprovação humana"

    return html.Div([
        dbc.Alert([
            html.Strong("Processamento automático"),
            html.Span(f" — {title}", className="ms-1"),
        ], color=banner_variant, className="small py-2 mb-2"),
        html.Ol(items, className="auto-pipeline-progress small mb-0"),
    ], className="auto-pipeline-banner mb-3")
