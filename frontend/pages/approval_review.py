"""Revisão e Aprovação por cálculo — fluxo canônico item a item."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.calculation_review.calculation_item_review_panel import CalculationItemReviewPanel
from components.calculation_review.calculation_review_table import CalculationReviewTable
from components.calculation_review.file_approval_final_panel import FileApprovalFinalPanel
from components.calculation_review.file_review_summary_cards import ReviewToolbar
from components.calculation_review.review_provenance_summary import ReviewProvenanceSummary
from components.calculation_review.result_version_timeline import ResultVersionTimeline
from components.empty_state import EMPTY_NO_PENDING_APPROVAL, EmptyFilterState, EmptyState
from components.page_header import PageHeader
from services.calculation_approval_service import ensure_review_started
from services.calculation_review_service import ensure_calculation_review
from services.cycle_status_service import count_pending_approval, cycles_pending_approval
from services.page_context import resolve_page_context


def _audit_section(cycle: dict) -> html.Div:
    return html.Div([
        dbc.Accordion([
            dbc.AccordionItem(
                html.Div([
                    html.Div(ResultVersionTimeline(cycle), className="mb-3"),
                    ReviewProvenanceSummary(cycle),
                ]),
                title="Auditoria — versões e proveniência",
            ),
        ], start_collapsed=True, className="cr-audit-accordion"),
    ], className="mb-3")


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    pending = cycles_pending_approval(ctx.cycles)
    reviewable = [c for c in ctx.cycles if c.get("calculation")]
    queue = pending or reviewable
    selected = ctx.active_cycle if ctx.active_cycle.get("cycle_id") else (queue[0] if queue else {})

    if selected.get("calculation"):
        selected = ensure_calculation_review(selected)
        selected = ensure_review_started(selected)

    pending_count = count_pending_approval(ctx.cycles)

    body = [
        PageHeader(
            "Revisão e Aprovação",
            f"Conferência humana por cálculo. {pending_count} arquivo(s) pendente(s).",
            ctx.global_filter,
            filter_options,
            cycle=selected,
        ),
    ]

    if not queue and ctx.is_empty:
        body.append(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
        return html.Div(body, className="page-approval page-content-inner")

    if not queue:
        body.append(html.Div(
            EmptyState(
                EMPTY_NO_PENDING_APPROVAL["title"],
                EMPTY_NO_PENDING_APPROVAL["message"],
                icon=EMPTY_NO_PENDING_APPROVAL["icon"],
                action_label="Ir para Cálculos",
                action_href="/calculations",
            ),
            className="empty-state-container",
        ))
        return html.Div(body, className="page-approval page-content-inner")

    review_items = (selected.get("calculation_review") or {}).get("items") or []
    default_item_id = review_items[0].get("calculation_item_id") if review_items else None

    return html.Div(body + [
        ReviewToolbar(queue, selected),
        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody(
                    CalculationReviewTable(selected),
                ), className="agro-card mb-3"),
                FileApprovalFinalPanel(selected),
            ], lg=5, md=12, className="cr-workbench-left"),
            dbc.Col(
                html.Div(
                    id="cr-detail-panel",
                    children=CalculationItemReviewPanel(selected, default_item_id),
                    className="h-100",
                ),
                lg=7, md=12,
            ),
        ], className="g-3 mb-3 cr-workbench"),
        _audit_section(selected),
    ], className="page-approval page-content-inner")
