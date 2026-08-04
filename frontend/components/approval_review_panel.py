"""Painel canônico de revisão e aprovação humana."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.calculation_summary_card import CalculationSummaryCard
from components.cards import AlertBox
from components.emission_breakdown_chart import EmissionBreakdownChart
from components.empty_state import EmptyState
from components.key_value_table import KeyValueTable
from components.managerial_status import ApprovalStatusBadge
from components.tables import DataTable
from services.blockchain_view_service import build_evidence_summary
from services.calculation_view_service import (
    build_approval_view,
    build_calculation_parameters,
    build_source_breakdown,
)
from services.cycle_status_service import resolve_managerial_status
from utils.global_filter import format_cycle_period_label


def _params_readable(params: dict) -> list[dict]:
    gwp = params.get("gwp") or {}
    rows = [
        {"Parâmetro": "Metodologia", "Valor": params.get("methodology", "—")},
        {"Parâmetro": "Versão cálculo", "Valor": params.get("calculation_version", "—")},
        {"Parâmetro": "Versão canônica", "Valor": params.get("canonical_version", "—")},
        {"Parâmetro": "GWP CH₄", "Valor": gwp.get("CH4", "—")},
        {"Parâmetro": "GWP N₂O", "Valor": gwp.get("N2O", "—")},
    ]
    return rows


def ApprovalReviewPanel(cycle: dict, *, readonly: bool = False) -> html.Div:
    if not cycle or not cycle.get("cycle_id"):
        return html.Div(
            EmptyState(
                "Selecione um cálculo",
                "Escolha um item na fila de revisão para conferir o resultado preliminar.",
                icon="fas fa-hand-pointer",
            ),
            className="approval-review-panel",
        )

    st = resolve_managerial_status(cycle)
    params = build_calculation_parameters(cycle)
    sources = build_source_breakdown(cycle)
    approval = build_approval_view(cycle)
    quality_alerts = [
        w.get("message", str(w)) for w in (cycle.get("warnings") or [])
        if isinstance(w, dict)
    ][:5]

    sections: list = []

    if st.key in ("pending_approval", "calculation_preliminary"):
        sections.append(html.Div(
            AlertBox(
                "Este cálculo está pronto para decisão humana. Revise os valores, parâmetros e alertas antes de aprovar ou reprovar.",
                variant="pending",
                title="Pendente de aprovação",
            ),
            className="approval-pending-banner",
        ))

    sections.append(html.Div([
        html.Div([
            html.H5(f"{cycle.get('property_name', '—')} — {format_cycle_period_label(cycle)}", className="section-title mb-1"),
            html.P(f"Ciclo {cycle.get('cycle_id', '—')}", className="text-aux mb-2"),
            ApprovalStatusBadge(st),
        ]),
    ], className="approval-section"))

    sections.append(html.Div([
        CalculationSummaryCard(cycle, show_sources=True),
    ], className="approval-section"))

    sections.append(html.Div([
        html.H6("Emissões por fonte", className="card-title"),
        EmissionBreakdownChart(sources),
        DataTable(sources, columns=["fonte", "co2e_kg"] if sources else []),
    ], className="approval-section"))

    sections.append(html.Div([
        html.H6("Parâmetros utilizados", className="card-title"),
        DataTable(_params_readable(params), columns=["Parâmetro", "Valor"] if params else []),
    ], className="approval-section"))

    if quality_alerts:
        sections.append(html.Div([
            html.H6("Alertas de qualidade", className="card-title"),
            html.Ul([html.Li(a, className="text-aux") for a in quality_alerts]),
        ], className="approval-section"))

    if approval.get("decision") and approval.get("decision") not in ("PENDENTE", "PENDING", None):
        sections.append(html.Div([
            html.H6("Histórico de decisão", className="card-title"),
            KeyValueTable({
                "Decisão": approval.get("decision"),
                "Aprovador": approval.get("approver"),
                "Data": approval.get("approved_at"),
                "Justificativa": approval.get("justification"),
            }),
        ], className="approval-section"))

    if not readonly and st.key in ("pending_approval", "calculation_preliminary"):
        action_children: list = [
            html.H6("Decisão do revisor", className="card-title"),
            dbc.Row([
                dbc.Col(dbc.Input(id="approval-user", placeholder="Nome do revisor", value=""), md=4),
                dbc.Col(dbc.Textarea(id="approval-justification", placeholder="Justificativa da decisão", value=""), md=8),
            ], className="mb-3 g-2"),
            dbc.ButtonGroup([
                dbc.Button("Aprovar", id="btn-approve", size="sm", className="btn-agro-approve"),
                dbc.Button("Reprovar", id="btn-reject", size="sm", className="btn-agro-reject"),
                dbc.Button("Solicitar correção", id="btn-request-correction", size="sm", className="btn-agro-secondary"),
            ], className="mb-2 approval-actions"),
            html.Small(
                "Ao aprovar, o sistema publica a versão final, gera evidências, Merkle Root, ancoragem e verificação automaticamente.",
                className="text-aux d-block mb-2",
            ),
        ]
        sections.append(html.Div(action_children, className="approval-section"))

    if st.key in ("published", "evidence_generated", "integrity_verified"):
        summary = build_evidence_summary(cycle)
        sections.append(html.Div([
            html.H6("Pós-aprovação (automático)", className="card-title"),
            KeyValueTable({
                "Pacote de evidências": summary.get("evidence_package_id", "—"),
                "Merkle Root": summary.get("merkle_root", "—"),
                "Transação (simulada)": summary.get("transaction_id", "—"),
                "Integridade": (cycle.get("integrity") or {}).get("final_status", "—"),
            }),
            html.A("Detalhes técnicos → Auditoria Técnica", href="/technical-audit", className="small"),
        ], className="approval-section"))

    return html.Div(sections, className="approval-review-panel")
