"""Componentes de status gerencial."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from services.cycle_status_service import ManagerialStatus, resolve_managerial_status, traceability_summary


def ApprovalStatusBadge(status: ManagerialStatus | None = None, *, cycle: dict | None = None) -> html.Span:
    if not status and (not cycle or not cycle.get("cycle_id")):
        return html.Span()
    st = status or resolve_managerial_status(cycle)
    suffix = " (preliminar)" if st.key == "calculation_preliminary" else ""
    if st.is_official:
        suffix = ""
    return html.Span(
        f"{st.label}{suffix}",
        className=f"badge-status badge-status-{st.variant} me-1",
        title=st.next_action or "",
    )


def CycleStatusChip(cycle: dict | None) -> html.Div:
    if not cycle or not cycle.get("cycle_id"):
        return html.Div()
    st = resolve_managerial_status(cycle)
    return html.Div([
        html.Small("Status: ", className="text-muted"),
        ApprovalStatusBadge(st),
        html.Small(
            f" • {cycle.get('property_name', '—')} / {cycle.get('reporting_period', '—')}",
            className="text-aux ms-1",
        ),
    ], className="cycle-status-chip mb-2")


def EvidenceStatusCard(cycle: dict) -> dbc.Card:
    t = traceability_summary(cycle)
    items = []
    if t["traceability_available"]:
        items.append(html.Span("Rastreabilidade disponível", className="badge-status badge-status-dados-reais me-1"))
    if t["evidence_generated"]:
        items.append(html.Span("Evidência técnica gerada", className="badge-status badge-status-aprovado me-1"))
    if t["integrity_verified"]:
        items.append(html.Span("Integridade verificada", className="badge-status badge-status-aprovado me-1"))
    if not items:
        items.append(html.Span("Rastreabilidade pendente", className="badge-status badge-status-pendente me-1"))
    return dbc.Card(dbc.CardBody([
        html.H6("Rastreabilidade e evidência", className="card-title"),
        html.Div(items, className="mb-2"),
        dbc.Button("Abrir Auditoria Técnica", href="/technical-audit", color="secondary", outline=True, size="sm"),
    ]), className="agro-card")
