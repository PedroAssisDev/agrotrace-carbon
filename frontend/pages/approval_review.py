"""Revisão e Aprovação por cálculo — fluxo canônico item a item."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.calculation_review.approval_reviewer_fields import ApprovalReviewerFields
from components.calculation_review.calculation_item_review_panel import CalculationItemReviewPanel
from components.calculation_review.calculation_review_table import CalculationReviewTable
from components.calculation_review.file_approval_final_panel import FileApprovalFinalPanel
from components.calculation_review.file_review_selector import FileReviewSelector
from components.calculation_review.file_review_summary_cards import (
    CalculationReviewSummaryCards,
    FileReviewSummaryCards,
)
from components.calculation_review.review_provenance_summary import ReviewProvenanceSummary
from components.empty_state import EMPTY_NO_PENDING_APPROVAL, EmptyFilterState, EmptyState
from components.page_header import PageHeader
from components.status_badges import StatusBadge
from services.blockchain_view_service import is_blockchain_unlocked
from services.calculation_approval_service import ensure_review_started
from services.calculation_review_service import ensure_calculation_review, resolve_file_review_status
from services.cycle_status_service import count_pending_approval, cycles_pending_approval
from services.page_context import resolve_page_context


def _header_badges(cycle: dict) -> html.Div:
    calc = cycle.get("calculation") or {}
    review_st = resolve_file_review_status(cycle)
    bc = is_blockchain_unlocked(cycle)
    pub = (cycle.get("steps") or {}).get("publication", {})
    published = pub.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"}

    badges = [
        StatusBadge("PRELIMINARY", label="Resultado preliminar"),
        StatusBadge(review_st, label=review_st),
        StatusBadge("PROVENANCE", label="Proveniência ativa"),
    ]
    if published:
        badges.append(StatusBadge("APPROVED", label="Aprovado / Publicado"))
    else:
        badges.append(StatusBadge("BLOCKCHAIN_LOCKED", label="Blockchain bloqueado" if not bc else "Blockchain liberado"))

    raw = cycle.get("raw_file") or {}
    if raw.get("original_filename"):
        badges.append(html.Span(raw["original_filename"], className="badge-status badge-status-dados-reais me-1 small"))

    return html.Div(badges, className="d-flex flex-wrap gap-1 mt-2 cr-header-badges")


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

    body.append(_header_badges(selected))

    review_items = (selected.get("calculation_review") or {}).get("items") or []
    default_item_id = review_items[0].get("calculation_item_id") if review_items else None

    return html.Div(body + [
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody(
                FileReviewSelector(queue, selected.get("cycle_id")),
            ), className="agro-card"), md=12, className="mb-3"),
        ]),
        FileReviewSummaryCards(selected),
        CalculationReviewSummaryCards(selected),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody(ApprovalReviewerFields()), className="agro-card"), md=12),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody(
                CalculationReviewTable(selected),
            ), className="agro-card"), md=7),
            dbc.Col(
                html.Div(
                    id="cr-detail-panel",
                    children=CalculationItemReviewPanel(selected, default_item_id),
                ),
                md=5,
            ),
        ], className="g-3 mb-3"),
        FileApprovalFinalPanel(selected),
        ReviewProvenanceSummary(selected),
    ], className="page-approval page-content-inner")
