"""Revisão e Aprovação — fluxo canônico de governança humana."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.approval_review_panel import ApprovalReviewPanel
from components.empty_state import EMPTY_NO_PENDING_APPROVAL, EmptyFilterState, EmptyState
from components.page_header import PageHeader
from components.tables import DataTable
from services.cycle_status_service import count_pending_approval, cycles_pending_approval, resolve_managerial_status
from services.page_context import resolve_page_context
from utils.formatting import format_co2e
from utils.global_filter import format_cycle_period_label


def _queue_rows(cycles: list[dict]) -> list[dict]:
    rows = []
    for c in cycles:
        st = resolve_managerial_status(c)
        calc = c.get("calculation") or {}
        co2e = calc.get("co2e_total_kg")
        rows.append({
            "cycle_id": c.get("cycle_id"),
            "propriedade": c.get("property_name"),
            "periodo": format_cycle_period_label(c),
            "status": st.label,
            "co2e_kg": format_co2e(co2e) if co2e is not None else "—",
        })
    return rows


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    pending = cycles_pending_approval(ctx.cycles)
    all_review = [c for c in ctx.cycles if (c.get("calculation") or c.get("approval"))]
    queue = pending or all_review
    selected = ctx.active_cycle if ctx.active_cycle.get("cycle_id") else (queue[0] if queue else {})

    pending_count = count_pending_approval(ctx.cycles)

    body = [
        PageHeader(
            "Revisão e Aprovação",
            f"Conferência humana dos resultados preliminares de emissões. {pending_count} pendente(s).",
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

    return html.Div(body + [
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Fila de revisão", className="card-title mb-3"),
                html.Div(
                    DataTable(
                        _queue_rows(queue),
                        columns=["propriedade", "periodo", "status", "co2e_kg"] if queue else [],
                    ),
                    className="table-responsive",
                ),
                html.Small("Selecionar ciclo:", className="text-aux d-block mt-3"),
                dbc.Select(
                    id="approval-cycle-select",
                    options=[{"label": f"{r['propriedade']} — {r['periodo']}", "value": r["cycle_id"]} for r in _queue_rows(queue)],
                    value=selected.get("cycle_id"),
                    size="sm",
                    className="form-select-narrow mt-1",
                ),
            ]), className="agro-card h-100"), md=4),
            dbc.Col(ApprovalReviewPanel(selected), md=8),
        ], className="g-3"),
    ], className="page-approval page-content-inner")
