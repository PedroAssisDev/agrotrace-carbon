"""Indicadores e Relatórios — análise produtiva e ambiental."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, DataModeBadge, InsightAlert, SectionHeader
from components.dashboard_layout_helpers import build_indicator_tabs, section_body
from components.empty_state import EmptyFilterState, EmptyState
from components.page_header import PageHeader
from services import provenance_adapter
from services.cycle_status_service import resolve_managerial_status
from services.dashboard_service import (
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_dashboard_indicators,
    build_section_kpis,
    generate_dashboard_insights,
)
from services.data_availability import evaluate_widget_visibility
from services.farm_view_service import build_farm_profile
from services.page_context import resolve_page_context
from services.widget_registry import WIDGET_SPECS


def _filter_kpis(indicators: dict, section_key: str, cycle: dict, farm: dict) -> list[dict]:
    """Filtra KPIs de seção com base em disponibilidade de dados."""
    all_kpis = build_section_kpis(indicators, section_key)
    if not all_kpis:
        return []
    key_to_spec = {s.kpi_key: s for s in WIDGET_SPECS if s.section == section_key and s.kpi_key}
    filtered = []
    for kpi in all_kpis:
        title = kpi.get("title", "")
        spec = next((s for s in key_to_spec.values() if s.title == title), None)
        if spec:
            visible, _ = evaluate_widget_visibility(spec, cycle=cycle, indicators=indicators, property_profile=farm)
            if not visible:
                continue
        if kpi.get("value") in ("—", "N/A", None, ""):
            continue
        filtered.append(kpi)
    return filtered


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)

    if ctx.is_empty:
        return html.Div([
            PageHeader("Indicadores e Relatórios", "Métricas produtivas, ambientais e relatórios.", ctx.global_filter, filter_options),
            EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles),
        ], className="page-indicators page-content-inner")

    if ctx.no_official_data:
        return html.Div([
            PageHeader("Indicadores e Relatórios", "Métricas produtivas, ambientais e relatórios.", ctx.global_filter, filter_options),
            AlertBox(
                "Nenhum dado oficial disponível para este período. Altere o modo de dados para incluir preliminares.",
                variant="info",
            ),
        ], className="page-indicators page-content-inner")

    work_cycles = ctx.filtered_analysis_cycles or ctx.analysis_cycles
    events = provenance_adapter.list_events_for_context(
        ctx.global_filter, ctx.all_cycles, ctx.active_cycle, cycles_in_context=work_cycles, context_cycle_id=context_cycle_id,
    )
    indicators = build_dashboard_indicators(
        work_cycles, ctx.active_cycle, ctx.global_filter, events, ctx.all_cycles,
        temporal=ctx.temporal,
    )
    insights = generate_dashboard_insights(indicators)
    chart_series = build_dashboard_chart_components(build_dashboard_chart_series(indicators, work_cycles))
    meta = indicators.get("meta") or {}
    farm = build_farm_profile(ctx.active_cycle.get("property_id"), ctx.global_filter)
    st = resolve_managerial_status(ctx.active_cycle)

    official_note = []
    if meta.get("data_mode") == "include_preliminary" and meta.get("has_preliminary_data"):
        official_note.append(AlertBox(
            "Dados preliminares incluídos — resultados ainda não oficiais.",
            variant="warning",
            className="small",
        ))
    elif meta.get("data_mode") == "include_preliminary" and not meta.get("has_official_data"):
        official_note.append(AlertBox(
            "Indicadores de emissão exibidos como preliminares até aprovação e publicação.",
            variant="warning",
            className="small",
        ))
    agg = ctx.aggregated_approval_status or meta.get("aggregated_approval_status")
    if agg in ("partial_pending", "partial", "pending_approval"):
        official_note.append(AlertBox(
            "Período analítico com aprovação parcial ou pendente.",
            variant="pending",
            className="small",
        ))

    tab_sections = [
        ("prod", "Produtividade", None, section_body(
            _filter_kpis(indicators, "productivity", ctx.active_cycle, farm),
            chart_series["productivity"],
        )),
        ("manejo", "Manejo", None, section_body(
            _filter_kpis(indicators, "management", ctx.active_cycle, farm),
            chart_series.get("management") or [],
        )),
        ("env", "Emissões", None, section_body(
            _filter_kpis(indicators, "emissions", ctx.active_cycle, farm),
            chart_series["emissions"],
        )),
        ("sus", "Sustentabilidade", None, section_body(
            _filter_kpis(indicators, "sustainability", ctx.active_cycle, farm),
            chart_series["sustainability"],
        )),
        ("ger", "Gerenciamento", None, section_body(
            _filter_kpis(indicators, "business", ctx.active_cycle, farm),
            chart_series.get("business") or [],
        )),
        ("qual", "Qualidade", "Qualidade dos Dados", section_body(
            _filter_kpis(indicators, "data_quality", ctx.active_cycle, farm),
            chart_series["data_quality"],
        )),
        ("insights", "Insights", None, [
            html.Div(
                [InsightAlert(i) for i in insights] or [
                    EmptyState(
                        "Nenhum insight disponível",
                        "Os insights são gerados a partir dos indicadores do ciclo ativo.",
                        icon="fas fa-lightbulb",
                    ),
                ],
            ),
        ]),
        ("reports", "Relatórios", None, [
            AlertBox("Exportação completa em breve. Use as abas analíticas para consulta.", variant="info", className="small mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.I(className="fas fa-file-alt text-aux mb-2 d-block", style={"fontSize": "1.5rem"}),
                    html.H6("Relatório de emissões", className="card-title"),
                    html.P(f"{len(ctx.analysis_cycles)} ciclo(s) no escopo analítico.", className="text-aux mb-2"),
                    dbc.Button("Ver indicadores", href="/indicators", size="sm", className="btn-agro-secondary report-preview-btn", disabled=True),
                ]), className="agro-card report-card"), md=4),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.I(className="fas fa-graduation-cap text-aux mb-2 d-block", style={"fontSize": "1.5rem"}),
                    html.H6("Relatório para dissertação", className="card-title"),
                    html.P("Evidências técnicas e trilha de auditoria completa.", className="text-aux mb-2"),
                    dbc.Button("Auditoria Técnica", href="/technical-audit", size="sm", className="btn-agro-primary report-preview-btn"),
                ]), className="agro-card report-card"), md=4),
            ], className="g-3"),
        ]),
    ]

    return html.Div([
        PageHeader("Indicadores e Relatórios", "Métricas produtivas, ambientais e relatórios.", ctx.global_filter, filter_options, cycle=ctx.active_cycle),
        html.Div([DataModeBadge(meta.get("data_mode")), *official_note], className="mb-2"),
        build_indicator_tabs(tab_sections),
    ], className="page-indicators page-content-inner")
