"""Painel de origem e qualidade dos dados."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, SectionHeader
from components.emission_detail.scope import ScopeBadge


def _summary_line(label: str, value) -> html.Div:
    return html.Div([
        html.Span(f"{label}: ", className="text-aux"),
        html.Strong(str(value) if value not in (None, "") else "—"),
    ], className="mb-1")


def _variable_badge(label: str, *, variant: str) -> html.Span:
    cls = {
        "found": "emission-origin-badge emission-origin-badge--real",
        "missing": "emission-origin-badge emission-origin-badge--default",
        "default": "emission-origin-badge emission-origin-badge--fallback",
    }.get(variant, "emission-origin-badge")
    return html.Span(label, className=cls)


def EmissionDataOriginPanel(origin: dict, *, cycle_id: str | None, period: str | None) -> html.Div:
    alerts: list = []
    if origin.get("is_fallback"):
        alerts.append(AlertBox("Valor default/fallback usado porque o dado não foi encontrado no arquivo.", variant="warning"))
    if origin.get("is_mock"):
        alerts.append(AlertBox("Cálculo executado com dados simulados (mock).", variant="warning"))

    summary_items = [
        ("Arquivo de origem", origin.get("original_filename")),
        ("Hash do arquivo", origin.get("file_hash")),
        ("Lote normalizado", origin.get("normalized_batch_id")),
        ("Registros usados", origin.get("record_count", 0)),
        ("Origem do cálculo", origin.get("data_source")),
        ("Modo", origin.get("mode")),
        ("Hash preliminar", origin.get("preliminary_hash")),
        ("Versão ontologia", origin.get("ontology_version")),
    ]

    var_badges: list = []
    for v in origin.get("variables_found") or []:
        var_badges.append(_variable_badge(v, variant="found"))
    for v in origin.get("variables_missing") or []:
        var_badges.append(_variable_badge(f"{v} (ausente)", variant="missing"))
    for v in origin.get("variables_default") or []:
        var_badges.append(_variable_badge(f"{v} (default)", variant="default"))

    children: list = [
        SectionHeader("Origem dos dados usados no cálculo"),
        ScopeBadge(consolidated=False, cycle_id=cycle_id, period=period),
        *alerts,
        dbc.Card(dbc.CardBody([
            *[_summary_line(label, value) for label, value in summary_items],
        ]), className="agro-card mb-3"),
    ]

    if var_badges:
        children.append(dbc.Card(dbc.CardBody([
            html.H6("Variáveis de entrada", className="card-title"),
            html.Div(var_badges, className="d-flex flex-wrap gap-1"),
        ]), className="agro-card mb-3"))
    elif origin.get("legacy_schema"):
        children.append(html.P(
            "Resolução de entradas não registrada (schema legado).",
            className="text-aux small mb-0",
        ))

    return html.Div(children, className="emission-detail-section mb-4")
