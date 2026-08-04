"""Tabela de arquivos enviados — Entrada de Dados."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def _status_badge(label: str, variant: str) -> html.Span:
    return html.Span(label, className=f"badge-status badge-status-{variant} me-1")


def DataEntryFilesTable(rows: list[dict], *, selected_cycle_id: str | None = None) -> html.Div:
    """Tabela principal com hash resumido, status e ações por arquivo."""
    if not rows:
        return html.Div("Nenhum arquivo no período.", className="empty-state small")

    header = html.Thead(html.Tr([
        html.Th("Arquivo"),
        html.Th("Fazenda"),
        html.Th("Período"),
        html.Th("Layout/tipo"),
        html.Th("Data de envio"),
        html.Th("Hash resumido"),
        html.Th("Status"),
        html.Th("Próxima ação"),
        html.Th("Ações"),
    ]))

    body_rows = []
    for r in rows:
        cid = r.get("cycle_id")
        is_selected = cid and cid == selected_cycle_id
        row_cls = "data-entry-row data-entry-row--selected" if is_selected else "data-entry-row"
        actions = [
            dbc.Button(
                "Ver detalhes",
                id={"type": "data-entry-detail", "cycle": cid},
                size="sm",
                outline=True,
                className="btn-agro-secondary me-1",
            ),
        ]
        if r.get("next_href") == "/approval":
            actions.append(dbc.Button(
                "Ir para Revisão",
                href="/approval",
                size="sm",
                className="btn-agro-primary",
            ))
        body_rows.append(html.Tr([
            html.Td(r.get("arquivo", "—"), className="small"),
            html.Td(r.get("fazenda", "—"), className="small"),
            html.Td(r.get("periodo", "—"), className="small"),
            html.Td(r.get("layout", "—"), className="small"),
            html.Td(r.get("data_envio", "—"), className="small text-aux"),
            html.Td(html.Code(r.get("hash_resumido", "—"), className="hash-mono small")),
            html.Td(_status_badge(r.get("status", "—"), r.get("status_variant", "pendente"))),
            html.Td(r.get("proxima_acao", "—"), className="small text-aux"),
            html.Td(html.Div(actions, className="d-flex flex-wrap gap-1")),
        ], className=row_cls))

    return html.Div(
        html.Table([header, html.Tbody(body_rows)], className="table table-sm agro-table data-entry-table mb-0"),
        className="table-responsive",
    )
