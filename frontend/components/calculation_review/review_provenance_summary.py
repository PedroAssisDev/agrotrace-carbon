"""Resumo de proveniência da revisão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.tables import DataTable
from services.review_provenance_service import list_review_events


def ReviewProvenanceSummary(cycle: dict) -> html.Div:
    events = list_review_events(cycle)
    rows = []
    for e in events[-10:]:
        rows.append({
            "evento": e.get("event_type") or e.get("type", "—"),
            "quando": (e.get("created_at") or e.get("timestamp") or "—")[:19],
            "detalhe": str(e.get("calculation_item_id") or e.get("decision") or e.get("reviewer") or "—")[:40],
        })

    return dbc.Card(dbc.CardBody([
        html.Div([
            html.H6("Proveniência da revisão", className="card-title mb-0"),
            html.A("Ver na Auditoria Técnica", href="/technical-audit", className="small"),
        ], className="d-flex justify-content-between align-items-center mb-3"),
        DataTable(rows, columns=["evento", "quando", "detalhe"]) if rows else html.P(
            "Nenhum evento de revisão registrado ainda.", className="text-muted small mb-0",
        ),
    ]), className="agro-card cr-provenance-summary")
