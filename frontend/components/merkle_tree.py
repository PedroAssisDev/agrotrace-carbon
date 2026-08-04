"""Visualização simplificada da Merkle Tree."""

from __future__ import annotations

from dash import html

from components.cards import AlertBox
from utils.hash_helpers import truncate_hash


def MerkleTreeView(evidence: dict | None, hashes: dict | None = None) -> html.Div:
    if not evidence and not hashes:
        return html.Div("Nenhum pacote de evidências disponível.", className="empty-state text-muted")

    merkle_root = (evidence or {}).get("merkle_root", "—")
    items = list((hashes or evidence or {}).get("hashes", hashes or {}).items())
    if not items and hashes:
        items = list(hashes.items())

    leaves = []
    for i, (name, h) in enumerate(items):
        leaves.append(
            html.Div([
                html.Small(name, className="text-muted d-block"),
                html.Code(truncate_hash(str(h), 16), className="small"),
            ], className="merkle-leaf agro-card p-2 mb-1")
        )

    return html.Div([
        html.Div([
            html.Strong("Merkle Root", className="card-title"),
            html.Div(truncate_hash(str(merkle_root), 32), className="hash-mono hash-highlight mt-2"),
        ], className="text-center mb-3"),
        html.H6("Folhas (artefatos)", className="section-title mb-2"),
        html.Div(leaves if leaves else [html.Small("Itens do pacote serão exibidos após a construção.", className="text-aux")]),
        AlertBox(
            "A raiz Merkle agrega os hashes dos itens de evidência em uma única âncora verificável.",
            variant="info",
            className="mt-3 small",
        ),
    ], className="agro-card p-3")
