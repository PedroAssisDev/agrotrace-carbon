"""Cabeçalho contextual e visão geral da Análise Geral."""

from __future__ import annotations

from dash import html

from components.cards import AlertBox, KpiGrid, SectionHeader
from components.mode_badge import DataModeBadge, IntegrationModeBadge
from services.general_analysis_service import context_message
from services.indicator_chart_service import build_executive_temporal_section
from services.general_analysis_service import build_overview_kpis


def AnalysisContextBanner(meta: dict) -> list:
    banners = []
    msg = context_message(meta)
    if msg:
        variant = "warning" if meta.get("includes_preliminary") else "info"
        banners.append(AlertBox(msg, variant=variant, className="small"))
    if meta.get("aggregated_approval_status") in ("partial_pending", "partial", "pending_approval"):
        banners.append(AlertBox(
            "Período analítico com aprovação parcial ou pendente.",
            variant="pending", className="small",
        ))
    return banners


def AnalysisBadgesRow(meta: dict) -> html.Div:
    return html.Div([
        DataModeBadge(meta.get("data_mode")),
        IntegrationModeBadge(meta.get("integration_mode")),
    ], className="analysis-badges-row mb-2 d-flex flex-wrap gap-1 align-items-center")


def OverviewSection(indicators: dict) -> list:
    meta = indicators.get("meta") or {}
    kpis = build_overview_kpis(indicators)
    body: list = [
        AnalysisBadgesRow(meta),
        html.Div(AnalysisContextBanner(meta), className="mb-2"),
        SectionHeader("Indicadores principais", subtitle="Resumo consolidado da fazenda no período selecionado."),
        KpiGrid(kpis, col_md=4) if kpis else html.Div(),
        build_executive_temporal_section(indicators, title="Evolução temporal"),
    ]
    return body
