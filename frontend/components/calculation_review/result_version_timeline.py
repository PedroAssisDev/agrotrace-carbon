"""Linha do tempo de versões de resultado (RF010)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from services.result_correction_service import (
    compare_versions,
    get_active_version,
    list_result_versions,
)


def ResultVersionTimeline(cycle: dict) -> html.Div:
    versions = list_result_versions(cycle)
    if not versions:
        return html.Div(
            html.P("Nenhuma versão de resultado registrada ainda.", className="text-muted small mb-0"),
            className="cr-version-timeline",
        )

    active = get_active_version(cycle) or {}
    active_id = active.get("version_id")
    corrections = {c.get("correction_id"): c for c in (cycle.get("corrections") or [])}

    cards = []
    for i, v in enumerate(versions):
        vid = v.get("version_id")
        status = v.get("status") or "—"
        corr = corrections.get(v.get("correction_id") or "") if v.get("correction_id") else None
        justification = (corr or {}).get("justification") or "—"
        totals = v.get("totals") or {}
        prev_totals = v.get("previous_totals") or {}
        co2e = totals.get("co2e_total_kg")
        prev_co2e = prev_totals.get("co2e_total_kg")

        compare_block = html.Div()
        if v.get("supersedes") and i > 0:
            cmp = compare_versions(cycle, v["supersedes"], vid)
            changed = [r for r in (cmp.get("rows") or []) if r.get("changed")]
            compare_block = html.Div([
                html.P(
                    f"Total anterior: {cmp.get('previous_total')} → novo: {cmp.get('new_total')}",
                    className="small mb-1",
                ),
                html.Ul(
                    [
                        html.Li(
                            f"{r['formula']}: {r.get('previous')} → {r.get('new')}",
                            className="small",
                        )
                        for r in changed[:8]
                    ]
                    or [html.Li("Sem alteração numérica detectada.", className="small text-muted")],
                    className="mb-0 ps-3",
                ),
            ])

        is_active = vid == active_id
        needs_review = status == "preliminary" and is_active and any(
            it.get("status") == "ADJUSTMENT_PENDING_RECALCULATION"
            for it in ((cycle.get("calculation_review") or {}).get("items") or [])
        )

        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.Div([
                        html.Strong(vid or f"v{i+1}", className="me-2"),
                        dbc.Badge(status, color="primary" if is_active else "secondary", className="me-1"),
                        dbc.Badge("ativa", color="success") if is_active else html.Span(),
                    ], className="mb-2"),
                    html.P(f"CO₂e: {co2e if co2e is not None else '—'} kg", className="small mb-1"),
                    html.P(
                        f"Anterior: {prev_co2e if prev_co2e is not None else '—'} kg"
                        if prev_co2e is not None
                        else f"Hash: {(totals.get('preliminary_hash') or '—')[:16]}…",
                        className="small text-muted mb-1",
                    ),
                    html.P(f"Justificativa: {justification}", className="small mb-2"),
                    compare_block,
                    dbc.Button(
                        "Revisar nova versão",
                        id={"type": "cr-btn-review-version", "version": vid},
                        color="warning",
                        size="sm",
                        outline=True,
                        className="mt-2",
                    )
                    if needs_review
                    else html.Span(),
                ]),
                className="mb-2 agro-card",
            )
        )

    open_corr = [c for c in (cycle.get("corrections") or []) if c.get("status") == "open"]
    open_block = html.Div()
    if open_corr:
        c0 = open_corr[-1]
        fields = c0.get("correctable_fields") or []
        open_block = dbc.Alert(
            [
                html.Strong("Correção aberta: "),
                html.Span(c0.get("justification") or "—"),
                html.Br(),
                html.Span(
                    "Campos corrigíveis: "
                    + ", ".join(f.get("field") or f.get("label") or "?" for f in fields[:6]),
                    className="small",
                ),
            ],
            color="warning",
            className="py-2",
        )

    return html.Div([
        html.H6("Histórico de versões (RF010)", className="mb-2"),
        open_block,
        *cards,
    ], className="cr-version-timeline mb-3", id="cr-version-timeline")
