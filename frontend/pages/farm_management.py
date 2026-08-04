"""Fazendas e Períodos — cadastro resumido e histórico de ciclos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import KpiGrid, SectionHeader
from components.cycle_history_table import CycleHistoryTable
from components.cycle_status_timeline import CycleStatusTimeline
from components.empty_state import EmptyFilterState
from components.managerial_status import ApprovalStatusBadge
from components.page_header import PageHeader
from services.farm_view_service import build_farm_indicators, build_farm_profile
from services.page_context import resolve_page_context
from utils.formatting import format_co2e, format_intensity, format_number


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    farm = build_farm_profile(ctx.active_cycle.get("property_id"), ctx.global_filter)

    if ctx.is_empty:
        return html.Div([
            PageHeader("Fazendas e Períodos", "Propriedades, períodos de reporte e histórico de ciclos.", ctx.global_filter, filter_options),
            EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles),
        ], className="page-farm page-content-inner")

    ind = build_farm_indicators(ctx.cycles, ctx.active_cycle, ctx.global_filter, [])
    kpis = []
    if ind.get("production_total") is not None:
        kpis.append({"title": "Produção total (L)", "value": format_number(ind.get("production_total")), "icon": "fas fa-chart-line", "color": "primary"})
    if ind.get("kg_co2e_per_liter") is not None:
        kpis.append({"title": "kg CO₂e/L", "value": format_intensity(ind.get("kg_co2e_per_liter")), "icon": "fas fa-leaf", "color": "success"})
    if ind.get("emissions_per_animal") is not None:
        kpis.append({"title": "Emissões/animal", "value": format_co2e(ind.get("emissions_per_animal")), "icon": "fas fa-cloud", "color": "danger"})

    return html.Div([
        PageHeader("Fazendas e Períodos", "Propriedades, períodos de reporte e histórico de ciclos.", ctx.global_filter, filter_options, cycle=ctx.active_cycle),
        dbc.Card(dbc.CardBody([
            SectionHeader("Dados cadastrais"),
            html.P(f"{farm.get('name', '—')} — {farm.get('municipality', '')}/{farm.get('state', '')}"),
            html.P(f"Área: {farm.get('total_area_ha', '—')} ha • Produção: {farm.get('production_type', '—')} • Animais: {farm.get('animal_count', '—')}"),
            html.P(f"Responsável: {farm.get('technical_responsible', '—')}", className="text-aux"),
            ApprovalStatusBadge(cycle=ctx.active_cycle),
        ]), className="agro-card mb-3"),
        CycleStatusTimeline(ctx.active_cycle),
        KpiGrid(kpis, col_md=4) if kpis else None,
        SectionHeader("Histórico de ciclos"),
        CycleHistoryTable(ctx.cycles),
    ], className="page-farm page-content-inner")
