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
from services.blockchain_linkage_view_service import build_linkage_rows, build_linkage_trail
from services.blockchain_view_service import build_evidence_summary


def AuditBlockchainGate(
    cycle: dict,
    *,
    unlocked: bool,
    lock_message: str,
    approval_status: str,
    publication_status: str,
    pkg_rows: list[dict] | None = None,
    scoped_package_count: int = 0,
) -> html.Div:
    if not cycle.get("cycle_id"):
        return html.Div("Selecione um ciclo para auditar blockchain.", className="empty-state")

    if not unlocked:
        scope_hint = None
        if scoped_package_count > 0:
            scope_hint = html.P(
                f"Há {scoped_package_count} pacote(s) de evidência em outros ciclos do escopo. "
                "Selecione um ciclo publicado no seletor acima para auditar ancoragem e Merkle.",
                className="small text-info mt-2 mb-0",
            )
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
                scope_hint,
            ]), className="agro-card blockchain-gate-card"),
        )

    summary = build_evidence_summary(cycle)
    evidence = cycle.get("evidence_package") or {}
    anchoring = cycle.get("anchoring") or {}
    hashes = summary.get("hashes") or {}
    mode = summary.get("mode") or evidence.get("mode")
    trail = build_linkage_trail(cycle)
    linkage_rows = build_linkage_rows(trail)

    return html.Div([
        html.Div([
            html.H5("Evidências e blockchain", className="section-title d-inline-block me-2"),
            MockSourceBadge(mode, label="Blockchain" if mode == "mock" else None),
        ], className="mb-3"),
        dbc.Tabs([
            dbc.Tab(label="Resumo", tab_id="bc-resumo", children=html.Div([
                DataTable(
                    pkg_rows or [],
                    columns=["ciclo", "propriedade", "período", "pacote", "status"],
                ) if pkg_rows else html.P("Nenhum pacote no escopo.", className="text-muted small"),
                BlockchainAnchorCard(evidence, anchoring),
            ], className="mt-3")),
            dbc.Tab(label="Pacote", tab_id="bc-pacote", children=html.Div(EvidencePackageViewer(evidence), className="mt-3")),
            dbc.Tab(label="Hashes", tab_id="bc-hashes", children=html.Div(HashViewer(hashes), className="mt-3")),
            dbc.Tab(label="Merkle Root", tab_id="bc-merkle", children=html.Div(MerkleTreeView(evidence, hashes), className="mt-3")),
            dbc.Tab(label="Vínculo proveniência", tab_id="bc-vinculo", children=html.Div([
                html.P(
                    "Trilha reconstruída via adapters (provenance.db + ciclo). "
                    "Sem consulta direta ao SQLite do blockchain-service.",
                    className="text-muted small mb-2",
                ),
                DataTable(
                    linkage_rows,
                    columns=["etapa", "identificador", "presente"],
                ),
                html.P(
                    f"Completa: {'sim' if trail.get('complete') else 'não'} · "
                    f"pipeline_run_id: {trail.get('pipeline_run_id') or '—'}",
                    className="small mt-2 mb-0",
                ),
            ], className="mt-3")),
            dbc.Tab(label="Detalhes", tab_id="bc-detalhes", children=html.Div([
                html.P(f"Pacote: {summary.get('evidence_package_id', '—')}", className="small"),
                html.P(f"Rede: {summary.get('network', '—')}", className="small"),
                html.P(f"Tipo: {summary.get('anchoring_kind', '—')}", className="small"),
                html.P(f"Merkle Root: {summary.get('merkle_root', '—')}", className="small"),
                html.P([
                    html.Span("Tx: "),
                    html.Span(str(summary.get("transaction_id") or "—"), className="hash-mono small"),
                ], className="small"),
                html.P(f"Status ancoragem: {summary.get('anchoring_status', '—')}", className="small"),
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-external-link-alt me-2"), "Abrir transação no Etherscan Sepolia"],
                        href=summary["explorer_url"],
                        target="_blank",
                        rel="noopener noreferrer",
                        color="primary",
                        size="sm",
                        className="me-2 mb-2",
                        external_link=True,
                    ) if summary.get("explorer_url") else html.P(
                        "Link do explorador disponível após ancoragem real na Sepolia.",
                        className="small text-muted mb-2",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-file-contract me-2"), "Abrir contrato no Etherscan"],
                        href=f"https://sepolia.etherscan.io/address/{summary['contract_address']}",
                        target="_blank",
                        rel="noopener noreferrer",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="mb-2",
                        external_link=True,
                    ) if (
                        summary.get("network") == "ethereum_sepolia"
                        and summary.get("contract_address")
                        and str(summary.get("contract_address")).startswith("0x")
                    ) else None,
                ], className="mt-2"),
            ], className="mt-3")),
        ], id="ta-blockchain-inner-tabs", active_tab="bc-resumo", className="agro-tabs"),
    ])
