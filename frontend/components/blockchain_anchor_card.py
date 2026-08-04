"""Card de ancoragem blockchain."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.status_badges import StatusBadge
from utils.hash_helpers import truncate_hash


def BlockchainAnchorCard(evidence: dict | None, anchoring: dict | None = None) -> dbc.Card:
    evidence = evidence or {}
    anchoring = anchoring or {}
    merged = {**evidence, **anchoring}
    merkle = str(merged.get("merkle_root", "—"))
    network = merged.get("network", "local_simulated")
    kind = merged.get("anchoring_kind") or (
        "SIMULADA" if network == "local_simulated" else "CONFIRMADA EM REDE EVM"
    )
    tx = str(merged.get("transaction_id", merged.get("transaction_hash", "—")))
    explorer = merged.get("explorer_url")
    tx_children: list = [
        html.Strong("Transaction: "),
        html.Span(truncate_hash(tx, 20), className="hash-mono"),
    ]
    if (
        explorer
        and network == "ethereum_sepolia"
        and tx.startswith("0x")
        and kind != "SIMULADA"
    ):
        tx_children.append(html.Span(" · "))
        tx_children.append(html.A("Abrir no explorador", href=explorer, target="_blank", rel="noopener"))

    rows = [
        dbc.Col(html.P([html.Strong("Tipo: "), html.Span(kind, className="fw-semibold")]), md=6),
        dbc.Col(html.P([html.Strong("Package ID: "), merged.get("evidence_package_id", "—")]), md=6),
        dbc.Col(
            html.P([
                html.Strong("Status: "),
                StatusBadge(merged.get("anchoring_status", evidence.get("anchoring_status", "PENDING"))),
            ]),
            md=6,
        ),
        dbc.Col(html.P([html.Strong("Rede: "), network]), md=6),
        dbc.Col(html.P([html.Strong("Chain ID: "), merged.get("chain_id", "—")]), md=6),
        dbc.Col(html.P([html.Strong("Contrato: "), html.Span(truncate_hash(str(merged.get("contract_address", "—")), 16), className="hash-mono")]), md=6),
        dbc.Col(html.P([html.Strong("Evidence Key: "), html.Span(truncate_hash(str(merged.get("evidence_key", "—")), 18), className="hash-mono")]), md=6),
        dbc.Col(html.P(tx_children), md=6),
        dbc.Col(html.P([html.Strong("Bloco: "), merged.get("block_number", "—")]), md=6),
        dbc.Col(html.P([html.Strong("Gas: "), merged.get("gas_used", "—")]), md=6),
        dbc.Col(html.P([html.Strong("Submitter: "), html.Span(truncate_hash(str(merged.get("submitter", "—")), 14), className="hash-mono")]), md=6),
        dbc.Col(html.Div([
            html.Strong("Package Hash: "),
            html.Div(truncate_hash(str(merged.get("package_hash", "—")), 32), className="hash-mono mt-1"),
        ]), md=12),
        dbc.Col(html.Div([
            html.Strong("Merkle Root: "),
            html.Div(truncate_hash(merkle, 32), className="hash-mono hash-highlight mt-1"),
        ]), md=12),
    ]
    return dbc.Card([
        dbc.CardHeader("Ancoragem Blockchain", className="card-title"),
        dbc.CardBody([dbc.Row(rows)]),
    ], className="agro-card mb-3 mt-3")
