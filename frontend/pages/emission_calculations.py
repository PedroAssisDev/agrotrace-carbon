"""Cálculos de Emissão — resultado preliminar (pipeline automática pós-upload)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.auto_pipeline_progress import AutoPipelineProgressBanner
from components.calculation_summary_card import CalculationSummaryCard
from components.cards import AlertBox
from components.emission_breakdown_chart import EmissionBreakdownChart
from components.empty_state import EmptyFilterState
from components.managerial_status import ApprovalStatusBadge, CycleStatusChip
from components.page_header import PageHeader
from components.tables import DataTable
from services.calculation_view_service import build_preliminary_result, build_source_breakdown
from services.cycle_status_service import resolve_managerial_status
from services.page_context import resolve_page_context


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    c = ctx.active_cycle
    st = resolve_managerial_status(c)

    if ctx.is_empty and not c.get("calculation"):
        return html.Div([
            PageHeader("Cálculos de Emissão", "Execução do inventário de emissões.", ctx.global_filter, filter_options, cycle=c),
            EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles),
        ], className="page-calculations page-content-inner")

    prelim = build_preliminary_result(c)
    sources = build_source_breakdown(c)

    actions = []
    auto_done = st.key in ("pending_approval", "approved", "published", "evidence_generated", "integrity_verified")
    if not auto_done and st.key in ("data_integrated", "calculation_pending"):
        actions.append(dbc.Button("Calcular emissões (manual)", id="btn-run-calculation", color="secondary", outline=True, size="sm", className="me-2"))
    if not auto_done and st.key == "calculation_preliminary":
        actions.append(dbc.Button("Enviar para revisão (manual)", id="btn-send-for-review", color="secondary", outline=True, size="sm", className="me-2"))
    if st.key == "pending_approval" or c.get("current_status") == "AWAITING_HUMAN_APPROVAL":
        actions.append(AlertBox("Resultado preliminar pronto — aguardando aprovação humana.", variant="pending", className="small"))
        actions.append(dbc.Button("Abrir Revisão e Aprovação", href="/approval", size="sm", className="btn-agro-primary ms-2"))
    elif st.key in ("published", "evidence_generated", "integrity_verified"):
        actions.append(AlertBox("Ciclo aprovado e publicado. Consulte Auditoria Técnica para evidências.", variant="success", className="small"))

    return html.Div([
        PageHeader("Cálculos de Emissão", "Resultado preliminar — sujeito a aprovação humana.", ctx.global_filter, filter_options, cycle=c),
        CycleStatusChip(c),
        html.Div([ApprovalStatusBadge(st)], className="mb-2"),
        AutoPipelineProgressBanner(c),
        dbc.Card(dbc.CardBody([
            html.Div(actions, className="mb-3"),
            CalculationSummaryCard(c) if c.get("calculation") else html.Div(
                "Importe um arquivo na Entrada de Dados para processamento automático.",
                className="text-aux",
            ),
        ]), className="agro-card status-card mb-3"),
        dbc.Card(dbc.CardBody([
            EmissionBreakdownChart(sources),
            html.Div(DataTable(sources, columns=["fonte", "co2e_kg"] if sources else []), className="table-responsive mt-2"),
        ]), className="agro-card mb-3") if sources else None,
        html.P(f"Metodologia: {(c.get('calculation') or {}).get('methodology', 'IPCC / GEE agropecuário')}", className="text-aux"),
    ], className="page-calculations page-content-inner")
