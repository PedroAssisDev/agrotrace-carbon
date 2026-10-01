"""Card de ancoragem blockchain."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.status_badges import StatusBadge
from utils.hash_helpers import truncate_hash

_SEPOLIA_EXPLORER = "https://sepolia.etherscan.io"


def _resolve_explorer_url(merged: dict, network: str, tx: str, kind: str) -> str | None:
    explorer = merged.get("explorer_url")
    if explorer:
        return str(explorer)
    if (
        network == "ethereum_sepolia"
        and kind != "SIMULADA"
        and tx.startswith("0x")
        and len(tx) >= 66
    ):
        return f"{_SEPOLIA_EXPLORER}/tx/{tx}"
    return None


def _resolve_contract_url(network: str, contract: str | None) -> str | None:
    if network != "ethereum_sepolia" or not contract:
        return None
    addr = str(contract)
    if not addr.startswith("0x") or len(addr) < 42:
        return None
    return f"{_SEPOLIA_EXPLORER}/address/{addr}"


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
    contract = merged.get("contract_address")
    explorer = _resolve_explorer_url(merged, network, tx, kind)
    contract_url = _resolve_contract_url(str(network), str(contract) if contract else None)

    tx_children: list = [
        html.Strong("Transaction: "),
        html.Span(truncate_hash(tx, 20), className="hash-mono"),
    ]
    if explorer:
        tx_children.append(html.Span(" · "))
        tx_children.append(
            html.A("Abrir no explorador", href=explorer, target="_blank", rel="noopener noreferrer")
        )

    explorer_actions = []
    if explorer:
        explorer_actions.append(
            dbc.Button(
                [html.I(className="fas fa-external-link-alt me-2"), "Ver transação no Etherscan Sepolia"],
                href=explorer,
                target="_blank",
                rel="noopener noreferrer",
                color="primary",
                outline=True,
                size="sm",
                className="me-2 mb-1",
                external_link=True,
            )
        )
    if contract_url:
        explorer_actions.append(
            dbc.Button(
                [html.I(className="fas fa-file-contract me-2"), "Ver contrato no Etherscan"],
                href=contract_url,
                target="_blank",
                rel="noopener noreferrer",
                color="secondary",
                outline=True,
                size="sm",
                className="mb-1",
                external_link=True,
            )
        )

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
        dbc.Col(html.P([html.Strong("Contrato: "), html.Span(truncate_hash(str(contract or "—"), 16), className="hash-mono")]), md=6),
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
    if explorer_actions:
        rows.append(dbc.Col(html.Div(explorer_actions, className="mt-2"), md=12))

    return dbc.Card([
        dbc.CardHeader("Ancoragem Blockchain", className="card-title"),
        dbc.CardBody([dbc.Row(rows)]),
    ], className="agro-card mb-3 mt-3")
