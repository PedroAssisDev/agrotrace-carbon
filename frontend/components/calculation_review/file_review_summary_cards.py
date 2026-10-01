"""Toolbar única de contexto do arquivo em revisão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.calculation_review.file_review_selector import FileReviewSelector
from services.blockchain_view_service import is_blockchain_unlocked
from services.calculation_review_service import build_file_summary, build_review_summary_cards


def _stat_chip(title: str, value: str | int, tone: str = "") -> html.Div:
    extra = f" cr-stat-chip--{tone}" if tone else ""
    return html.Div([
        html.Span(title, className="cr-stat-chip-label"),
        html.Span(str(value), className="cr-stat-chip-value"),
    ], className=f"cr-stat-chip{extra}")


def ReviewToolbar(cycles: list[dict], selected: dict) -> html.Div:
    """Toolbar compacta: select + meta do ciclo atual + emissão + progresso."""
    fs = build_file_summary(selected)
    s = build_review_summary_cards(selected)
    bc_unlocked = is_blockchain_unlocked(selected)
    pub = (selected.get("steps") or {}).get("publication", {})
    published = pub.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"}
    queue_count = len([c for c in cycles if c.get("calculation")])

    meta_bits = [
        html.Span(f"{fs['farm']} · {fs['period']}", className="small text-aux"),
    ]
    if not bc_unlocked and not published:
        meta_bits.append(html.Span(" · Blockchain bloqueado", className="small text-warning"))

    children = [
        dbc.Row([
            dbc.Col(
                FileReviewSelector(cycles, selected.get("cycle_id")),
                md=4, lg=3,
            ),
            dbc.Col([
                html.Div(meta_bits, className="mb-1"),
                html.Div([
                    html.Strong("Emissão total: ", className="small"),
                    html.Span(s["emissions_display"], className="cr-emissions-total"),
                    html.Span(
                        f" · Aprovados {s['progress_label']}",
                        className="small text-aux ms-2",
                    ),
                    html.Span(
                        f" · {queue_count} arquivo(s) na fila",
                        className="small text-aux ms-2",
                    ),
                ], className="d-flex flex-wrap align-items-baseline gap-1"),
            ], md=5, lg=6),
            dbc.Col([
                html.Div([
                    _stat_chip("Pendentes", s["pending"], "warning"),
                    _stat_chip("Com zero", s["with_zero"]),
                    _stat_chip("Rejeitados", s["rejected"], "danger"),
                ], className="cr-stat-strip"),
            ], md=3, lg=3),
        ], className="g-2 align-items-end"),
        html.Div([
            dbc.Button(
                "Detalhes do arquivo",
                id="cr-toggle-file-details",
                color="link",
                size="sm",
                className="p-0 mt-2",
            ),
            dbc.Collapse(
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.Strong("Arquivo: "), fs["filename"],
                            ], className="small mb-1"),
                            html.P([
                                html.Strong("Layout: "), fs["layout"],
                            ], className="small mb-1"),
                            html.P([
                                html.Strong("Hash: "),
                                html.Span(fs["hash_short"], className="font-monospace"),
                                dbc.Collapse(
                                    html.Code(fs.get("hash_full") or "—", className="small d-block mt-1"),
                                    id="cr-hash-collapse",
                                ),
                                dbc.Button(
                                    "ver completo",
                                    id="cr-toggle-hash",
                                    color="link",
                                    size="sm",
                                    className="p-0 ms-1",
                                ),
                            ], className="small mb-1"),
                            html.P([
                                html.Strong("Linhas lidas/válidas/rejeitadas: "),
                                f"{fs['rows_read']}/{fs['rows_valid']}/{fs['rows_rejected']}",
                            ], className="small mb-1"),
                            html.P([html.Strong("Avisos: "), fs["warnings_count"]], className="small mb-0"),
                        ], md=6),
                        dbc.Col([
                            html.H6("Modelo canônico", className="small mb-2"),
                            html.P([html.Strong("Versão: "), fs.get("ontology_version", "—")], className="small mb-1"),
                            html.P([html.Strong("Entidades: "), fs.get("ontology_entities", 0)], className="small mb-1"),
                            html.P([
                                html.Strong("Variáveis no snapshot: "),
                                fs.get("canonical_var_count", 0),
                            ], className="small mb-1"),
                            html.P([
                                html.Strong("Hash ontologia: "),
                                html.Span(fs.get("ontology_hash_short", "—"), className="font-monospace"),
                            ], className="small mb-1"),
                            html.P([html.Strong("Status: "), fs.get("ontology_status", "—")], className="small mb-0"),
                        ], md=6),
                    ]),
                ], className="cr-file-details-body mt-2 p-2"),
                id="cr-file-details-collapse",
                is_open=False,
            ),
        ]),
    ]

    return dbc.Card(dbc.CardBody(children, className="py-3"), className="agro-card mb-3 cr-review-toolbar")


def FileReviewSummaryCards(cycle: dict) -> html.Div:
    """Compat: use ReviewToolbar(cycles, selected) na página."""
    return ReviewToolbar([cycle] if cycle.get("calculation") else [], cycle)


def CalculationReviewSummaryCards(cycle: dict) -> html.Div:
    """Compat: KPIs vivem na toolbar."""
    return html.Div(className="cr-calc-summary d-none")
