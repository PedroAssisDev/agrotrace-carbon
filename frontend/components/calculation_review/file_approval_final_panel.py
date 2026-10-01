"""Barra de finalização da aprovação do arquivo."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.calculation_review.approval_reviewer_fields import ApprovalReviewerFields
from services.calculation_approval_service import can_finalize


_PUBLISHED_STEP_STATUSES = frozenset({"DONE", "DONE_WARNINGS", "COMPLETED"})


def FileApprovalFinalPanel(cycle: dict) -> html.Div:
    ok, msg = can_finalize(cycle)
    pub = (cycle.get("steps") or {}).get("publication", {})
    published = pub.get("status") in _PUBLISHED_STEP_STATUSES

    return dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col(ApprovalReviewerFields(), md=7, lg=8),
            dbc.Col([
                dbc.Button(
                    "Finalizar aprovação do arquivo",
                    id="cr-btn-finalize",
                    color="primary",
                    disabled=not ok or published,
                    className="w-100",
                ),
                dbc.Alert(
                    msg,
                    color="success" if ok else "warning",
                    className="mt-2 mb-0 py-2 small",
                ),
                html.Div(id="cr-finalize-feedback", className="small mt-1"),
            ], md=5, lg=4, className="d-flex flex-column justify-content-end"),
        ], className="g-3 align-items-stretch"),
    ], className="py-3"), className="agro-card cr-final-panel mb-3")
