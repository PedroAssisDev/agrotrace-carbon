"""Painel Executivo — visão gerencial de alto nível."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, DataModeBadge, InsightAlert
from components.conditional_widgets import ConditionalChartSection, ConditionalKpiGrid
from components.emission_breakdown_chart import EmissionBreakdownChart
from components.empty_state import EmptyFilterState
from components.managerial_status import EvidenceStatusCard
from components.page_header import PageHeader
from services.calculation_view_service import build_source_breakdown
from services.cycle_status_service import count_pending_approval, resolve_managerial_status
from services.dashboard_service import (
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_dashboard_indicators,
    generate_dashboard_insights,
)
from services.farm_view_service import build_farm_profile
from services.page_context import resolve_page_context
from services import provenance_adapter


def _managerial_insights(indicators: dict) -> list:
    insights = generate_dashboard_insights(indicators)
    skip_types = {"auditoria"}
    return [i for i in insights if i.get("type") not in skip_types][:3]


def _governance_banners(ctx, indicators: dict) -> list:
    meta = indicators.get("meta") or {}
    banners = []
    data_mode = meta.get("data_mode") or ctx.data_mode

    if ctx.no_official_data or meta.get("no_official_in_mode"):
        banners.append(AlertBox(
            "Nenhum dado oficial disponível para este período.",
            variant="info",
            className="small",
        ))
    elif data_mode == "include_preliminary" and meta.get("has_preliminary_data"):
        banners.append(AlertBox(
            "Dados preliminares incluídos — resultados ainda não oficiais.",
            variant="warning",
            className="small",
        ))
    elif data_mode == "include_preliminary" and not meta.get("has_official_data"):
        banners.append(AlertBox(
            "Dados preliminares — aguardando aprovação e publicação.",
            variant="pending",
            className="small",
        ))

    agg = ctx.aggregated_approval_status or meta.get("aggregated_approval_status")
    if agg in ("partial_pending", "partial", "pending_approval"):
        banners.append(AlertBox(
            "Período analítico com aprovação parcial ou pendente.",
            variant="pending",
            className="small",
        ))
    return banners


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    active = ctx.active_cycle

    if ctx.no_farm_selected or ctx.no_farm_cycles:
        return html.Div([
            PageHeader(
                "Painel Executivo",
                "Visão de alto nível — status, emissões e próximos passos.",
                ctx.global_filter,
                filter_options,
            ),
            EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles),
        ], className="dashboard-page page-content-inner")

    if ctx.no_official_data:
        return html.Div([
            PageHeader(
                "Painel Executivo",
                "Visão de alto nível — status, emissões e próximos passos.",
                ctx.global_filter,
                filter_options,
                cycle=active,
            ),
            AlertBox(
                "Nenhum dado oficial disponível para este período. Altere o modo de dados para incluir preliminares.",
                variant="info",
            ),
        ], className="dashboard-page page-content-inner")

    work_cycles = ctx.filtered_analysis_cycles or ctx.analysis_cycles
    events = provenance_adapter.list_events_for_context(
        ctx.global_filter, ctx.all_cycles, active, cycles_in_context=work_cycles, context_cycle_id=context_cycle_id,
    )
    indicators = build_dashboard_indicators(
        work_cycles, active, ctx.global_filter, events, ctx.all_cycles, temporal=ctx.temporal,
    )
    st = resolve_managerial_status(active)
    farm = build_farm_profile(active.get("property_id"), ctx.global_filter)
    sources = build_source_breakdown(active)
    pending = count_pending_approval(ctx.analysis_cycles)
    insights = _managerial_insights(indicators)
    chart_series = build_dashboard_chart_components(build_dashboard_chart_series(indicators, work_cycles))

    gov_banners = _governance_banners(ctx, indicators)
    meta = indicators.get("meta") or {}

    pending_banner = []
    if pending:
        pending_banner.append(AlertBox(
            f"{pending} cálculo(s) aguardando aprovação humana.",
            variant="pending",
            title="Ação necessária",
            className="small",
        ))
        pending_banner.append(
            dbc.Button("Revisar agora", href="/approval", size="sm", className="btn-agro-primary mb-3"),
        )

    next_step_block = []
    if st.next_action:
        href = st.next_href or "#"
        next_step_block.append(html.Div([
            html.Div([
                html.H6("Próximo passo", className="card-title mb-1"),
                html.P(st.next_action, className="text-aux mb-2"),
                dbc.Button("Continuar", href=href, size="sm", className="btn-agro-primary") if st.next_href else None,
            ], className="summary-card"),
        ], className="mb-3"))

    charts = []
    for section in ("productivity", "emissions", "sustainability"):
        charts.extend(chart_series.get(section) or [])
    chart = EmissionBreakdownChart(sources) if sources and active.get("calculation") else None
    if chart:
        charts.insert(0, chart)

    alerts_block = []
    if insights:
        alerts_block.append(html.Div([
            html.H6("Alertas relevantes", className="section-title mb-2"),
            html.Div([InsightAlert(i) for i in insights]),
        ], className="mb-3"))

    return html.Div([
        PageHeader(
            "Painel Executivo",
            "Visão de alto nível — status, emissões e próximos passos.",
            ctx.global_filter,
            filter_options,
            cycle=active,
        ),
        html.Div([DataModeBadge(meta.get("data_mode")), *gov_banners], className="mb-2"),
        html.Div(pending_banner),
        ConditionalKpiGrid("/", cycle=active, indicators=indicators, property_profile=farm, max_items=6),
        ConditionalChartSection(charts),
        html.Div(next_step_block),
        html.Div(alerts_block),
        EvidenceStatusCard(active),
    ], className="dashboard-page page-content-inner")
