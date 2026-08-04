"""Ciclos de Emissão — wizard guiado com 11 etapas."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cycle_select import CycleSelect
from components.emission_steps import step_children
from components.empty_state import EmptyFilterState
from components.mode_badge import ModeBadge
from components.extended_pipeline_stepper import ExtendedPipelineStepper
from components.step_card import StepCard
from components.tables import DataTable
from services.cycle_state import PIPELINE_STEP_DEFS, events_for_step, progress_pct
from services.page_context import resolve_page_context


def build_technical_pipeline_section(ctx, filter_options: dict) -> list:
    """Conteúdo do wizard técnico para Auditoria Técnica."""
    cycle = ctx.active_cycle
    gf = ctx.global_filter
    if ctx.is_empty and not cycle.get("cycle_id"):
        return [EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles)]

    rows = [{
        "cycle_id": c.get("cycle_id"),
        "property": c.get("property_name"),
        "period": c.get("reporting_period"),
        "status": c.get("current_status", c.get("status", "—")),
        "progress": f"{progress_pct(c)}%",
    } for c in ctx.cycles]

    tabs = []
    for step_def in PIPELINE_STEP_DEFS:
        children = step_children(step_def.step_id, cycle, gf, filter_options)
        show_run = step_def.step_id != "approval"
        events = events_for_step(cycle, step_def.step_id)
        card_body = StepCard(step_def.step_id, cycle, children=children, show_run=show_run)
        detail = html.Div(id={"type": "wizard-detail", "step": step_def.step_id}, className="mt-2")
        tabs.append(
            dbc.Tab(
                label=step_def.label.split(". ", 1)[-1][:28],
                tab_id=step_def.step_id,
                children=html.Div([
                    card_body,
                    detail,
                    html.H6("Eventos desta etapa", className="mt-3 small text-muted") if events else None,
                    html.Ul([html.Li(f"{e.get('event_type')} — {e.get('created_at', '')}") for e in events[:5]]) if events else None,
                ], className="pt-3"),
            )
        )

    return [
        *CycleSelect(ctx.cycles, cycle, select_id="filter-cycle-select"),
        ExtendedPipelineStepper(cycle),
        dbc.Card(dbc.CardBody([
            html.Div([
                html.Strong(f"Ciclo: {cycle.get('cycle_id', '—')}"),
                html.Span(
                    f" • {cycle.get('property_name', '—')} • {cycle.get('reporting_period', '—')}",
                    className="text-aux ms-2",
                ),
                html.Span(ModeBadge((cycle.get("steps") or {}).get("evidence", {}).get("mode")), className="ms-2"),
            ]),
            dbc.ButtonGroup([
                dbc.Button("Pipeline completo (demo)", id="btn-run-full-pipeline", color="warning", outline=True, size="sm", className="btn-agro-secondary"),
                dbc.Button("Carregar demo", id="btn-load-demo", color="secondary", outline=True, size="sm", className="btn-agro-secondary"),
            ], className="mt-2"),
            html.Small(
                "Modo demonstração: a execução «Pipeline completo (demo)» usa aprovação automática simulada.",
                className="text-aux d-block mt-2",
            ),
        ]), className="agro-card mb-3"),
        dbc.Tabs(id="wizard-tabs", active_tab=PIPELINE_STEP_DEFS[0].step_id, children=tabs, className="agro-tabs"),
        html.Hr(),
        html.H5("Histórico", className="section-title"),
        DataTable(rows, columns=["cycle_id", "property", "period", "status", "progress"] if rows else []),
    ]


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    """Legacy — redirecionado para /technical-audit via router."""
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    return html.Div(build_technical_pipeline_section(ctx, filter_options or {}), className="page-emission-cycles page-content-inner")
