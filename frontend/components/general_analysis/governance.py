"""Governança, proveniência, blockchain e integridade."""

from __future__ import annotations

from dash import html

from components.cards import KpiGrid, SectionHeader
from services.general_analysis_service import build_governance_kpis


def GovernanceSection(indicators: dict) -> list:
    kpis = build_governance_kpis(indicators)
    return [
        SectionHeader(
            "Governança e rastreabilidade",
            subtitle="Status dos ciclos, proveniência, evidências e integridade.",
        ),
        KpiGrid(kpis, col_md=3) if kpis else html.Div(),
    ]
