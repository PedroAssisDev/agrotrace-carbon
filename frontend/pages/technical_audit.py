"""Hub de Auditoria Técnica — pipeline, proveniência, blockchain e logs."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.empty_state import EmptyFilterState
from components.page_header import PageHeader
from pages.emission_cycles import build_technical_pipeline_section
from pages.technical_audit_sections import (
    build_blockchain_section,
    build_data_section,
    build_integrity_section,
    build_logs_section,
    build_ontology_section,
    build_provenance_section,
)
from services.page_context import resolve_page_context


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)

    body = [
        PageHeader(
            "Auditoria Técnica",
            "Pipeline técnica, proveniência, evidências criptográficas e verificação de integridade.",
            ctx.global_filter,
            filter_options,
            cycle=ctx.active_cycle,
            show_status=True,
        ),
    ]

    if ctx.is_empty and not ctx.active_cycle.get("cycle_id"):
        body.append(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))

    body.append(dbc.Tabs([
        dbc.Tab(label="Visão Técnica do Ciclo", tab_id="ta-pipeline", children=html.Div(
            build_technical_pipeline_section(ctx, filter_options or {}), className="pt-3",
        )),
        dbc.Tab(label="Dados Brutos e Normalizados", tab_id="ta-data", children=html.Div(
            build_data_section(ctx), className="pt-3",
        )),
        dbc.Tab(label="Ontologia e Validação", tab_id="ta-ontology", children=html.Div(
            build_ontology_section(ctx), className="pt-3",
        )),
        dbc.Tab(label="Proveniência", tab_id="ta-provenance", children=html.Div(
            build_provenance_section(ctx, context_cycle_id), className="pt-3",
        )),
        dbc.Tab(label="Evidências e Blockchain", tab_id="ta-blockchain", children=html.Div(
            build_blockchain_section(ctx), className="pt-3",
        )),
        dbc.Tab(label="Verificação de Integridade", tab_id="ta-integrity", children=html.Div(
            build_integrity_section(ctx), className="pt-3",
        )),
        dbc.Tab(label="Logs e Eventos", tab_id="ta-logs", children=html.Div(
            build_logs_section(ctx), className="pt-3",
        )),
    ], id="technical-audit-tabs", active_tab="ta-pipeline", className="agro-tabs"))

    return html.Div(body, className="page-technical-audit page-content-inner")
