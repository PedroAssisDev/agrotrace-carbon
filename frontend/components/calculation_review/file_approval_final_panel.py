"""Painel de finalização da aprovação do arquivo."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.status_badges import StatusBadge
from services.blockchain_view_service import is_blockchain_unlocked
from services.calculation_approval_service import can_finalize
from services.calculation_review_service import resolve_file_review_status


_PUBLISHED_STEP_STATUSES = frozenset({"DONE", "DONE_WARNINGS", "COMPLETED"})


def FileApprovalFinalPanel(cycle: dict) -> html.Div:
    ok, msg = can_finalize(cycle)
    review_status = resolve_file_review_status(cycle)
    bc_unlocked = is_blockchain_unlocked(cycle)
    pub = (cycle.get("steps") or {}).get("publication", {})
    published = pub.get("status") in _PUBLISHED_STEP_STATUSES

    return dbc.Card(dbc.CardBody([
        html.H6("Finalizar aprovação do arquivo", className="card-title mb-3"),
        dbc.Row([
            dbc.Col([
                html.P([html.Strong("Status revisão: "), StatusBadge(review_status, label=review_status)], className="small mb-1"),
                html.P([html.Strong("Blockchain: "), "Liberado" if bc_unlocked else "Bloqueado"], className="small mb-1"),
                html.P([html.Strong("Publicação: "), "Publicado" if published else "Pendente"], className="small mb-1"),
            ], md=8),
            dbc.Col([
                dbc.Button(
                    "Finalizar aprovação do arquivo",
                    id="cr-btn-finalize",
                    color="primary",
                    disabled=not ok or published,
                    className="w-100",
                ),
            ], md=4, className="d-flex align-items-center"),
        ]),
        dbc.Alert(msg, color="success" if ok else "warning", className="mt-2 mb-0 py-2 small"),
        html.Div(id="cr-finalize-feedback", className="small mt-2"),
    ]), className="agro-card cr-final-panel mb-3")
