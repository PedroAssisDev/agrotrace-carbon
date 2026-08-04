"""Gate e visualização blockchain para auditoria."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit.mock_source_badge import MockSourceBadge
from components.blockchain_anchor_card import BlockchainAnchorCard
from components.empty_state import EMPTY_BLOCKCHAIN_LOCKED, EmptyState
from components.evidence_package_viewer import EvidencePackageViewer
from components.hash_viewer import HashViewer
from components.merkle_tree import MerkleTreeView
from components.tables import DataTable
from services.blockchain_view_service import build_evidence_summary


def AuditBlockchainGate(
    cycle: dict,
    *,
    unlocked: bool,
    lock_message: str,
    approval_status: str,
    publication_status: str,
    pkg_rows: list[dict] | None = None,
) -> html.Div:
    if not cycle.get("cycle_id"):
        return html.Div("Selecione um ciclo para auditar blockchain.", className="empty-state")

    if not unlocked:
        return html.Div(
            dbc.Card(dbc.CardBody([
                html.I(className="fas fa-lock gate-icon d-block mb-2"),
                html.H5("Blockchain bloqueado", className="mb-3"),
                html.P(
                    "A evidência blockchain só pode ser criada após:",
                    className="mb-2",
                ),
                html.Ol([
                    html.Li("Aprovação humana do cálculo"),
                    html.Li("Publicação da versão final da ontologia"),
                ], className="mb-3"),
                html.Div([
                    html.Strong("Status atual:", className="d-block mb-1"),
                    html.P(f"Aprovação humana: {approval_status}", className="small mb-1"),
                    html.P(f"Publicação final: {publication_status}", className="small mb-2"),
                ]),
                EmptyState(
                    EMPTY_BLOCKCHAIN_LOCKED["title"],
                    lock_message or EMPTY_BLOCKCHAIN_LOCKED["message"],
                    icon=EMPTY_BLOCKCHAIN_LOCKED["icon"],
                    action_label="Ir para Aprovação",
                    action_href="/approval",
                ),
            ]), className="agro-card blockchain-gate-card"),
        )

    summary = build_evidence_summary(cycle)
    evidence = cycle.get("evidence_package") or {}
    anchoring = cycle.get("anchoring") or {}
    hashes = summary.get("hashes") or {}
    mode = summary.get("mode") or evidence.get("mode")

    return html.Div([
        html.Div([
            html.H5("Evidências e blockchain", className="section-title d-inline-block me-2"),
            MockSourceBadge(mode, label="Blockchain" if mode == "mock" else None),
        ], className="mb-3"),
        dbc.Tabs([
            dbc.Tab(label="Resumo", children=html.Div([
                DataTable(
                    pkg_rows or [],
                    columns=["ciclo", "propriedade", "período", "pacote", "status"],
                ) if pkg_rows else html.P("Nenhum pacote no escopo.", className="text-muted small"),
                BlockchainAnchorCard(evidence, anchoring),
            ], className="mt-3")),
            dbc.Tab(label="Pacote", children=html.Div(EvidencePackageViewer(evidence), className="mt-3")),
            dbc.Tab(label="Hashes", children=html.Div(HashViewer(hashes), className="mt-3")),
            dbc.Tab(label="Merkle Root", children=html.Div(MerkleTreeView(evidence, hashes), className="mt-3")),
            dbc.Tab(label="Detalhes", children=html.Div([
                html.P(f"Pacote: {summary.get('evidence_package_id', '—')}", className="small"),
                html.P(f"Merkle Root: {summary.get('merkle_root', '—')}", className="small"),
                html.P(f"Tx/Simulação: {summary.get('transaction_id', '—')}", className="small"),
                html.P(f"Status ancoragem: {summary.get('anchoring_status', '—')}", className="small"),
            ], className="mt-3")),
        ], className="agro-tabs"),
    ])
