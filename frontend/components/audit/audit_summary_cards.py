"""Cards do resumo da auditoria."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


_STATUS_CSS = {
    "Completo": "badge-status-aprovado",
    "OK": "badge-status-aprovado",
    "Liberado": "badge-status-aprovado",
    "Íntegro": "badge-status-aprovado",
    "Concluída": "badge-status-aprovado",
    "Dados reais": "badge-status-dados-reais",
    "Pendente": "badge-status-pendente",
    "Bloqueado": "badge-status-pendente",
    "Não verificado": "badge-status-pendente",
    "Dados simulados": "badge-status-fallback-mock",
    "Dados mistos": "badge-status-pendente",
    "Divergente": "badge-status-reprovado",
    "Erro": "badge-status-reprovado",
}


def _status_badge(status: str) -> html.Span:
    css = _STATUS_CSS.get(status, "badge-status-pendente")
    return html.Span(status, className=f"badge-status {css}")


def AuditSummaryCards(
    cards: list[dict],
    main_message: dict | None = None,
    banners: list[dict] | None = None,
) -> html.Div:
    blocks: list = []

    for banner in banners or []:
        variant = banner.get("variant", "warning")
        blocks.append(dbc.Alert([
            html.Strong(banner.get("title", ""), className="d-block"),
            html.Span(banner.get("message", "")),
        ], color=variant, className="mb-3 py-2 small"))

    if main_message:
        blocks.append(dbc.Alert([
            html.Strong(main_message.get("title", ""), className="d-block mb-1"),
            html.Span(main_message.get("message", "")),
        ], color=main_message.get("variant", "info"), className="mb-3"))

    if not cards:
        return html.Div(blocks)

    card_cols = []
    for c in cards:
        body = [
            html.H6(c.get("title", "—"), className="card-title small text-muted mb-1"),
            html.Div(_status_badge(c.get("status", "—")), className="mb-2"),
            html.P(c.get("description", ""), className="small mb-1"),
            html.Small(f"Serviço: {c.get('service', '—')}", className="text-aux d-block"),
        ]
        if c.get("action") and c.get("action_href"):
            body.append(html.A(c["action"], href=c["action_href"], className="small d-block mt-2"))
        card_cols.append(dbc.Col(
            dbc.Card(dbc.CardBody(body), className="agro-card audit-summary-card h-100"),
            md=6, lg=4, className="mb-3",
        ))

    blocks.append(dbc.Row(card_cols, className="g-2"))
    return html.Div(blocks, className="audit-summary-cards")
