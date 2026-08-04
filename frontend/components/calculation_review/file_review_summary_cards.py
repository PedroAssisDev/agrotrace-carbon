"""Cards de resumo do arquivo e dos cálculos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit.mock_source_badge import MockSourceBadge
from components.cards import AlertBox
from components.status_badges import StatusBadge
from services.blockchain_view_service import blockchain_lock_message, is_blockchain_unlocked
from services.calculation_review_service import build_file_summary, build_review_summary_cards


def _mini_card(title: str, value: str | int, css: str = "") -> dbc.Col:
    return dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6(title, className="small text-muted mb-1"),
            html.Div(str(value), className=f"cr-summary-value {css}"),
        ]), className="agro-card cr-summary-card h-100"),
        md=4, lg=2, className="mb-2",
    )


def FileReviewSummaryCards(cycle: dict) -> html.Div:
    fs = build_file_summary(cycle)
    bc_unlocked = is_blockchain_unlocked(cycle)
    pub = (cycle.get("steps") or {}).get("publication", {})
    published = pub.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"}
    children: list = [
        html.H6("Resumo do arquivo", className="card-title mb-3"),
    ]
    if not bc_unlocked and not published:
        children.append(AlertBox(
            blockchain_lock_message(cycle),
            variant="warning",
            title="Blockchain bloqueado durante revisão",
            className="small mb-3",
        ))
    children.extend([
        dbc.Row([
            dbc.Col([
                html.P([html.Strong("Arquivo: "), fs["filename"]], className="small mb-1"),
                html.P([html.Strong("Fazenda: "), fs["farm"]], className="small mb-1"),
                html.P([html.Strong("Período: "), fs["period"]], className="small mb-1"),
                html.P([html.Strong("Layout: "), fs["layout"]], className="small mb-1"),
            ], md=6),
            dbc.Col([
                html.P([
                    html.Strong("Hash: "),
                    html.Span(fs["hash_short"], className="font-monospace"),
                    dbc.Collapse(
                        html.Code(fs.get("hash_full") or "—", className="small d-block mt-1"),
                        id="cr-hash-collapse",
                    ),
                    dbc.Button("ver completo", id="cr-toggle-hash", color="link", size="sm", className="p-0 ms-1"),
                ], className="small mb-1"),
                html.P([html.Strong("Linhas lidas/válidas/rejeitadas: "),
                        f"{fs['rows_read']}/{fs['rows_valid']}/{fs['rows_rejected']}"], className="small mb-1"),
                html.P([html.Strong("Avisos: "), fs["warnings_count"]], className="small mb-1"),
                html.Div([
                    MockSourceBadge(fs["data_mode"]),
                    StatusBadge(fs["review_status"], label=fs["review_status"]),
                ], className="d-flex gap-1 flex-wrap"),
            ], md=6),
        ]),
        html.Hr(className="my-2"),
        html.H6("Modelo canônico", className="small mb-2"),
        dbc.Row([
            dbc.Col([
                html.P([html.Strong("Versão: "), fs.get("ontology_version", "—")], className="small mb-1"),
                html.P([html.Strong("Entidades: "), fs.get("ontology_entities", 0)], className="small mb-1"),
                html.P([html.Strong("Variáveis no snapshot: "), fs.get("canonical_var_count", 0)], className="small mb-1"),
            ], md=6),
            dbc.Col([
                html.P([
                    html.Strong("Hash ontologia: "),
                    html.Span(fs.get("ontology_hash_short", "—"), className="font-monospace"),
                ], className="small mb-1"),
                html.P([html.Strong("Status: "), fs.get("ontology_status", "—")], className="small mb-1"),
            ], md=6),
        ]),
    ])
    return dbc.Card(dbc.CardBody(children), className="agro-card mb-3 cr-file-summary")


def CalculationReviewSummaryCards(cycle: dict) -> html.Div:
    s = build_review_summary_cards(cycle)
    return html.Div([
        html.H6("Resumo dos cálculos", className="card-title mb-3"),
        dbc.Row([
            _mini_card("Total", s["total"]),
            _mini_card("Aprovados", s["approved"], "text-success"),
            _mini_card("Pendentes", s["pending"], "text-warning"),
            _mini_card("Com zero", s["with_zero"]),
            _mini_card("Ajustes", s["manual_adjustments"]),
            _mini_card("Rejeitados", s["rejected"], "text-danger"),
        ], className="g-2"),
    ], className="cr-calc-summary mb-3")
