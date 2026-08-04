"""Ranking e detalhe por fonte emissora."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import SectionHeader
from components.charts import ExecutiveEmissionSourcePieChart, GroupedBarChart, MultiLineTemporalChart, temporal_chart_empty_card
from components.emission_detail.scope import ScopeBadge
from services.emission_timeseries_service import (
    build_consolidated_source_from_ranking,
    build_source_line_series,
)
from utils.formatting import format_percent, format_t_co2e
from utils.temporal_model import TemporalModel


def EmissionSourceRanking(ranking: dict) -> html.Div:
    rows = ranking.get("rows") or []
    if not rows:
        return html.Div(
            html.P("Não há fontes emissoras para exibir.", className="text-aux"),
            className="emission-detail-section mb-4",
        )

    by_source_kg = {r["fonte"]: float(r.get("co2e_kg") or 0) for r in rows}
    pie = ExecutiveEmissionSourcePieChart(by_source_kg)

    return html.Div([
        SectionHeader("Emissões por fonte", "Ranking e participação no total"),
        ScopeBadge(consolidated=True),
        dbc.Card(dbc.CardBody([pie]), className="agro-card mb-0"),
    ], className="emission-detail-section mb-4")


def _source_series_has_values(by_source: dict) -> bool:
    for vals in (by_source or {}).values():
        if any(v is not None for v in vals):
            return True
    return False


def EmissionSourceLineChart(
    timeseries: dict,
    cycles: list[dict] | None = None,
    temporal: TemporalModel | None = None,
    source_ranking: dict | None = None,
) -> html.Div:
    """Evolução temporal por fonte emissora — uma curva por fonte, legenda clicável."""
    labels = timeseries.get("labels") or []
    by_source = timeseries.get("by_source") or {}

    if not _source_series_has_values(by_source) and cycles:
        labels, by_source = build_source_line_series(cycles, temporal)

    if not _source_series_has_values(by_source) and source_ranking:
        labels, by_source = build_consolidated_source_from_ranking(source_ranking)

    if not timeseries.get("has_series") and not labels:
        return html.Div([
            SectionHeader(
                "Evolução por fonte emissora",
                "Detalhamento temporal em t CO₂e",
            ),
            ScopeBadge(consolidated=True),
            temporal_chart_empty_card("Não há série temporal para o período filtrado."),
        ], className="emission-detail-section mb-4")

    chart = MultiLineTemporalChart(
        "Detalhamento por fonte emissora (t CO₂e)",
        labels,
        by_source,
        yaxis_title="t CO₂e",
        min_points=1,
    )

    body: list = [
        SectionHeader(
            "Evolução por fonte emissora",
            "Uma curva por fonte — clique na legenda para mostrar ou ocultar",
        ),
        ScopeBadge(consolidated=True),
    ]
    if chart is not None:
        body.append(dbc.Card(dbc.CardBody([chart]), className="agro-card mb-0"))
    else:
        body.append(html.P(
            "Não há dados temporais por fonte emissora para o período filtrado.",
            className="text-aux small mb-0",
        ))

    return html.Div(body, className="emission-detail-section mb-4")


def EntericTierComparisonPanel(tier: dict | None) -> html.Div:
    if not tier:
        return html.Div(
            html.P(
                "Não há dados Tier 2 observados para fermentação entérica neste arquivo.",
                className="text-aux small mb-0",
            ),
            className="emission-empty-hint p-2 mb-2",
        )

    tier1 = tier.get("tier1") or {}
    tier2 = tier.get("tier2") or {}
    t1_co2e_t = (tier1.get("co2e_kg") or 0) / 1000.0
    t2_co2e_t = (tier2.get("enteric_co2e_kg") or 0) / 1000.0

    chart = GroupedBarChart(
        "Entérica — Tier 1 calculado vs Tier 2 observado (t CO₂e)",
        ["Tier 1 (calculado)", "Tier 2 (ECOFARM observado)"],
        {"CO₂e": [t1_co2e_t, t2_co2e_t]},
    )

    delta_pct = tier.get("co2e_delta_pct")
    delta_kg = tier.get("co2e_delta_kg")

    return html.Div([
        html.H6("Comparação Tier 1 vs Tier 2 — fermentação entérica", className="card-title"),
        chart,
        html.Ul([
            html.Li(f"Tier 1: {format_t_co2e(t1_co2e_t)} — fórmula {tier1.get('formula', '—')}"),
            html.Li(f"Tier 2: {format_t_co2e(t2_co2e_t)} — fonte {tier2.get('source', 'ECOFARM')}"),
            html.Li(f"Diferença: {format_t_co2e((delta_kg or 0) / 1000.0)} ({format_percent(delta_pct) if delta_pct is not None else '—'})"),
        ], className="text-aux small mt-2"),
    ], className="enteric-tier-panel mb-2")


def _detail_body(detail: dict) -> list:
    body: list = []
    sub = detail.get("subcalculation") or {}
    if sub.get("formula"):
        body.append(html.P([html.Strong("Fórmula: "), sub["formula"]], className="small mb-1"))
    if sub.get("result_kg") is not None:
        body.append(html.P([html.Strong("Resultado: "), f"{sub.get('result_kg')} {sub.get('unit', '')}"], className="small mb-1"))
    if detail.get("co2e_t") is not None:
        body.append(html.P([html.Strong("CO₂e: "), format_t_co2e(detail["co2e_t"])], className="small mb-1"))

    inputs = detail.get("inputs") or {}
    if inputs:
        body.append(html.H6("Variáveis usadas", className="small mt-2"))
        body.append(html.Ul([html.Li(f"{k}: {v}", className="small text-aux") for k, v in inputs.items() if v is not None]))

    factors = detail.get("factors") or {}
    if factors:
        body.append(html.H6("Fatores", className="small mt-2"))
        body.append(html.Pre(str(factors)[:800], className="small text-aux bg-light p-2 rounded"))

    if detail.get("id") == "enteric":
        body.append(EntericTierComparisonPanel(detail.get("tier_comparison")))

    return body


def EmissionSourceDetailAccordion(details: list[dict], *, cycle_id: str | None, period: str | None) -> html.Div:
    if not details:
        return html.Div()

    items = []
    for i, d in enumerate(details):
        items.append(dbc.AccordionItem(
            _detail_body(d),
            title=f"{d.get('title', 'Fonte')} — {format_t_co2e(d.get('co2e_t'))}",
            item_id=f"emission-source-{d.get('id', i)}",
        ))

    return html.Div([
        SectionHeader("Detalhamento por fonte emissora", "Subcálculos e variáveis do ciclo ativo"),
        ScopeBadge(consolidated=False, cycle_id=cycle_id, period=period),
        dbc.Accordion(items, start_collapsed=True, flush=True, className="emission-source-accordion"),
    ], className="emission-detail-section mb-4")
