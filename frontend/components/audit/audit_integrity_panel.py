"""Painel de verificação de integridade."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit.mock_source_badge import MockSourceBadge
from components.integrity_comparison_table import IntegrityComparisonTable
from services.integrity_view_service import build_integrity_summary, integrity_message


def AuditIntegrityPanel(
    cycle: dict,
    pkg_options: list[dict],
    *,
    selected_cycle_id: str | None = None,
) -> html.Div:
    if not pkg_options:
        return html.Div(
            "Nenhum pacote de evidências disponível para verificação neste escopo.",
            className="empty-state",
        )

    display_cycle = cycle
    sel_id = selected_cycle_id or cycle.get("cycle_id", "")
    if selected_cycle_id and selected_cycle_id != cycle.get("cycle_id"):
        from utils.file_helpers import get_cycle
        loaded = get_cycle(selected_cycle_id)
        if loaded:
            display_cycle = loaded

    integrity = display_cycle.get("integrity") or {}
    summary = build_integrity_summary(display_cycle)
    message = integrity_message(integrity)
    evidence = display_cycle.get("evidence_package") or {}
    mode = integrity.get("mode") or evidence.get("mode")

    divergent_alert = None
    if integrity.get("is_valid") is False:
        divergent_alert = dbc.Alert(
            "Divergência detectada — há alteração ou inconsistência entre artefatos ancorados e recalculados.",
            color="danger",
            className="mb-3",
        )

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Select(
                id="verify-cycle-select",
                options=pkg_options,
                value=sel_id,
                size="sm",
            ), md=5),
            dbc.Col(dbc.ButtonGroup([
                dbc.Button("Executar verificação íntegra", id="btn-verify-intact", size="sm", className="btn-agro-approve"),
                dbc.Button("Simular divergência", id="btn-verify-tamper", size="sm", className="btn-agro-reject"),
            ]), md=7),
        ], className="mb-3 g-2"),
        divergent_alert,
        html.Div([
            MockSourceBadge(mode),
            html.Span(f" {message}", className="text-aux ms-2"),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Small("Pacote selecionado", className="text-muted d-block"),
                html.Strong(evidence.get("evidence_package_id", "—")),
            ], md=4),
            dbc.Col([
                html.Small("Merkle Root original", className="text-muted d-block"),
                html.Code((evidence.get("merkle_root") or "—")[:24] + "…" if evidence.get("merkle_root") else "—"),
            ], md=4),
            dbc.Col([
                html.Small("Merkle recalculada", className="text-muted d-block"),
                html.Code((integrity.get("merkle_root_recomputed") or "—")[:24] + "…" if integrity.get("merkle_root_recomputed") else "—"),
            ], md=4),
        ], className="mb-3 g-2 small"),
        html.P(f"Última verificação: {integrity.get('verified_at') or 'Nunca executada'}", className="small text-aux mb-2"),
        IntegrityComparisonTable({**integrity, "rows": summary.get("rows") or [], "message": message}),
    ], className="audit-integrity-panel")
