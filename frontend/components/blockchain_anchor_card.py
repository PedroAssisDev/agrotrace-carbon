"""Card de ancoragem blockchain."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.status_badges import StatusBadge
from utils.hash_helpers import truncate_hash


def BlockchainAnchorCard(evidence: dict | None, anchoring: dict | None = None) -> dbc.Card:
    evidence = evidence or {}
    anchoring = anchoring or {}
    merkle = str(evidence.get("merkle_root", "—"))
    return dbc.Card([
        dbc.CardHeader("Ancoragem Blockchain", className="card-title"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.P([html.Strong("Package ID: "), evidence.get("evidence_package_id", "—")]), md=6),
                dbc.Col(html.P([html.Strong("Status: "), StatusBadge(anchoring.get("anchoring_status", evidence.get("anchoring_status", "PENDING")))]), md=6),
                dbc.Col(html.P([html.Strong("Rede: "), anchoring.get("network", evidence.get("network", "local_simulated"))]), md=6),
                dbc.Col(html.P([
                    html.Strong("Transaction: "),
                    html.Span(truncate_hash(str(anchoring.get("transaction_id", evidence.get("transaction_id", "—"))), 20), className="hash-mono"),
                ]), md=6),
                dbc.Col(html.Div([
                    html.Strong("Merkle Root: "),
                    html.Div(truncate_hash(merkle, 32), className="hash-mono hash-highlight mt-1"),
                ]), md=12),
            ]),
        ]),
    ], className="agro-card mb-3 mt-3")
