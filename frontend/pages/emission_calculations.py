"""Cálculos de Emissão — detalhamento técnico e analítico de emissões."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, SectionHeader
from components.emission_detail import (
    EmissionCalcHeaderBadges,
    EmissionGasBreakdown,
    EmissionNextAction,
    EmissionOverviewCards,
    EmissionSourceRanking,
    EmissionSourceLineChart,
    EmissionTemporalSection,
    EmissionVariationCards,
)
from components.empty_state import EmptyFilterState
from components.page_header import PageHeader
from services.cycle_status_service import resolve_managerial_status
from services.emission_detail_service import build_emission_detail_bundle
from services.emission_source_breakdown_service import (
    build_gas_breakdown,
    build_source_ranking,
    build_variation_summary,
)
from services.emission_timeseries_service import build_emission_timeseries
from services.page_context import resolve_page_context


def _manual_actions(c: dict, st) -> list:
    actions: list = []
    auto_done = st.key in ("pending_approval", "approved", "published", "evidence_generated", "integrity_verified")
    if not auto_done and st.key in ("data_integrated", "calculation_pending"):
        actions.append(dbc.Button(
            "Calcular emissões (manual)", id="btn-run-calculation",
            color="secondary", outline=True, size="sm", className="me-2",
        ))
    if not auto_done and st.key == "calculation_preliminary":
        actions.append(dbc.Button(
            "Enviar para revisão (manual)", id="btn-send-for-review",
            color="secondary", outline=True, size="sm", className="me-2",
        ))
    return actions


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    c = ctx.active_cycle
    st = resolve_managerial_status(c)
    gf = ctx.global_filter

    if ctx.no_farm_selected:
        return html.Div([
            PageHeader("Cálculos de Emissão", "Detalhamento técnico de emissões de GEE.", gf, filter_options, cycle=c),
            EmptyFilterState(no_farm=True),
        ], className="page-calculations page-content-inner")

    if ctx.no_farm_cycles or (ctx.is_empty and not c.get("calculation")):
        return html.Div([
            PageHeader("Cálculos de Emissão", "Detalhamento técnico de emissões de GEE.", gf, filter_options, cycle=c),
            EmptyFilterState(no_farm_cycles=ctx.no_farm_cycles),
        ], className="page-calculations page-content-inner")

    work_cycles = ctx.filtered_analysis_cycles or ctx.analysis_cycles or ([c] if c.get("calculation") else [])
    if ctx.no_official_data:
        return html.Div([
            PageHeader("Cálculos de Emissão", "Detalhamento técnico de emissões de GEE.", gf, filter_options, cycle=c),
            AlertBox(
                "O filtro atual está em somente dados oficiais, mas só existem resultados preliminares.",
                variant="warning",
            ),
        ], className="page-calculations page-content-inner")

    timeseries = build_emission_timeseries(work_cycles, ctx.temporal)
    source_ranking = build_source_ranking(
        work_cycles, timeseries, all_cycles=ctx.all_cycles, global_filter=gf,
    )
    gas_breakdown = build_gas_breakdown(work_cycles, timeseries)
    variation = build_variation_summary(
        work_cycles, timeseries, all_cycles=ctx.all_cycles, global_filter=gf,
    )
    detail = build_emission_detail_bundle(c, work_cycles, gf, source_ranking, gas_breakdown)
    header_meta = detail["header"]

    sections: list = [
        PageHeader(
            "Cálculos de Emissão",
            None,
            gf, filter_options, cycle=c, show_status=False,
        ),
        EmissionCalcHeaderBadges(header_meta),
    ]

    manual = _manual_actions(c, st)
    if manual:
        sections.append(html.Div(manual, className="mb-3"))

    if not detail.get("has_calculation"):
        sections.append(AlertBox(
            "Não há cálculo preliminar para o ciclo selecionado. "
            "Importe dados na Entrada de Dados ou execute o cálculo manualmente.",
            variant="info",
        ))
    else:
        sections.extend([
            html.Div([
                SectionHeader("Indicadores principais", "Consolidado do período filtrado"),
                EmissionOverviewCards(detail.get("overview_cards") or []),
            ], className="emission-detail-section mb-4"),
            EmissionTemporalSection(timeseries),
            EmissionSourceRanking(source_ranking),
            EmissionSourceLineChart(timeseries, work_cycles, ctx.temporal, source_ranking),
            EmissionGasBreakdown(gas_breakdown),
            html.Div([
                SectionHeader("Variações no período", "Comparação entre o primeiro e o último período do filtro"),
                EmissionVariationCards(variation),
            ], className="emission-detail-section mb-4"),
        ])

    sections.append(EmissionNextAction(st, has_calculation=bool(c.get("calculation"))))

    return html.Div(sections, className="page-calculations page-content-inner emission-calculations-detail")
