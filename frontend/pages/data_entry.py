"""Entrada de Dados — upload e acompanhamento gerencial de arquivos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, KpiGrid, SectionHeader
from components.data_entry_files_table import DataEntryFilesTable
from components.empty_state import EmptyState
from components.farm_selector import FarmSelector
from components.file_detail_panel import FileDetailPanel
from components.page_header import PageHeader
from components.upload_form import RawUploadForm
from services.cycle_status_service import resolve_managerial_status
from services.data_view_service import (
    build_data_entry_overview,
    build_data_entry_rows,
    build_farm_upload_cycles,
    pick_latest_cycle,
    resolve_detail_cycle,
)
from services.page_context import PageContext, resolve_page_context
from utils.global_filter import VIEW_GRANULARITY_OPTIONS, normalize_global_filter


def _context_block(ctx: PageContext) -> html.Div:
    """Bloco discreto com contexto atual da fazenda e período filtrado."""
    cycles = ctx.cycles or []
    overview = build_data_entry_overview(cycles) if cycles else {}
    if overview.get("pending_approval"):
        status_geral = f"{overview['pending_approval']} aguardando aprovação"
    elif overview.get("with_error"):
        status_geral = f"{overview['with_error']} com erro"
    elif overview.get("total"):
        status_geral = f"{overview['total']} arquivo(s) no período"
    else:
        status_geral = "Nenhum arquivo no período"

    gran_label = VIEW_GRANULARITY_OPTIONS.get(ctx.view_granularity, ctx.view_granularity or "—")
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Small("Fazenda selecionada", className="gf-label d-block"),
                html.Strong(ctx.farm_name or "—", className="small"),
            ], md=3),
            dbc.Col([
                html.Small("Período filtrado", className="gf-label d-block"),
                html.Strong(ctx.period_display_label or ctx.period or "—", className="small"),
            ], md=3),
            dbc.Col([
                html.Small("Granularidade", className="gf-label d-block"),
                html.Strong(gran_label, className="small"),
            ], md=2),
            dbc.Col([
                html.Small("Status geral dos arquivos", className="gf-label d-block"),
                html.Strong(status_geral, className="small"),
            ], md=4),
        ], className="g-2 data-entry-context-block"),
    ], className="summary-card mb-3")


def _render_upload_feedback(upload_feedback: dict | None) -> html.Div | None:
    if not upload_feedback or not upload_feedback.get("message"):
        return None
    return AlertBox(
        upload_feedback["message"],
        variant=upload_feedback.get("variant", "info"),
        className="small mt-2",
    )


def _overview_metrics(overview: dict) -> list[dict]:
    return [
        {"title": "Total enviados", "value": overview.get("total", 0), "icon": "fas fa-file-upload", "color": "petrol"},
        {"title": "Processados com sucesso", "value": overview.get("processed", 0), "icon": "fas fa-check-circle", "color": "green"},
        {"title": "Com alerta", "value": overview.get("with_alert", 0), "icon": "fas fa-exclamation-triangle", "color": "amber"},
        {"title": "Com erro", "value": overview.get("with_error", 0), "icon": "fas fa-times-circle", "color": "red"},
        {"title": "Aguardando aprovação", "value": overview.get("pending_approval", 0), "icon": "fas fa-user-clock", "color": "blue"},
    ]


def _tab_section_styles(ctx: PageContext) -> tuple[dict, dict]:
    if ctx.no_farm_selected:
        return {}, {"display": "none"}
    return {"display": "none"}, {}


def _build_monitoring_section(
    ctx: PageContext,
    cycles: list[dict],
    context_cycle_id: str | None,
) -> list:
    if ctx.no_farm_selected:
        return [html.Div(
            EmptyState(
                "Nenhuma fazenda selecionada.",
                "Use o filtro global (barra superior) para escolher uma fazenda existente.",
                icon="fas fa-tractor",
            ),
            className="empty-state-container",
        )]

    if not cycles:
        if ctx.no_farm_cycles:
            return [html.Div(
                EmptyState(
                    "Nenhum ciclo encontrado para esta fazenda.",
                    "Envie um arquivo CSV para iniciar o primeiro processamento.",
                    icon="fas fa-seedling",
                ),
                className="empty-state-container",
            )]
        return [html.Div(
            EmptyState(
                "Nenhum arquivo enviado para a fazenda e período selecionados.",
                "Envie um CSV na área acima ou ajuste os filtros para visualizar outros períodos.",
                icon="fas fa-inbox",
            ),
            className="empty-state-container",
        )]

    overview = build_data_entry_overview(cycles)
    rows = build_data_entry_rows(cycles)
    farm_upload_cycles = build_farm_upload_cycles(ctx.all_cycles, ctx.farm_id)
    detail_cycle, selected_id = resolve_detail_cycle(
        farm_upload_cycles,
        ctx.active_cycle,
        context_cycle_id,
    )
    st = resolve_managerial_status(detail_cycle)

    section: list = [
        html.Div([
            SectionHeader("Acompanhamento no período"),
            KpiGrid(_overview_metrics(overview), col_md=2),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                SectionHeader("Arquivos enviados no período"),
                DataEntryFilesTable(rows, selected_cycle_id=selected_id),
            ]), className="agro-card h-100"), md=7),
            dbc.Col(
                FileDetailPanel(
                    detail_cycle,
                    cycles=farm_upload_cycles,
                    selected_cycle_id=selected_id,
                ),
                md=5,
            ),
        ], className="g-3 mb-3 data-entry-master-detail"),
    ]

    if st.key == "pending_approval":
        section.extend([
            AlertBox(
                "Processamento concluído. O resultado preliminar aguarda aprovação humana.",
                variant="pending",
                className="small",
            ),
            dbc.Button(
                "Ir para Revisão e Aprovação",
                href="/approval",
                size="sm",
                className="btn-agro-primary mb-3",
            ),
        ])

    return section


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
    upload_feedback: dict | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    cycles = ctx.cycles or []
    active = ctx.active_cycle if ctx.active_cycle.get("cycle_id") else {}
    if not active.get("cycle_id") and cycles:
        active = pick_latest_cycle(cycles)

    register_style, existing_style = _tab_section_styles(ctx)
    neutral_filter = normalize_global_filter({})
    upload_cycle = active if active.get("cycle_id") else (cycle or {})
    upload_filter = ctx.global_filter if not ctx.no_farm_selected else neutral_filter
    upload_cycle_props = upload_cycle if not ctx.no_farm_selected else {}

    body: list = [
        html.Div(
            PageHeader(
                "Entrada de Dados",
                "Cadastre uma nova fazenda e envie o arquivo CSV. "
                "Após o processamento, ela ficará disponível no filtro global.",
                show_status=False,
                global_filter=neutral_filter,
            ),
            id="de-farm-register-header",
            style=register_style,
        ),
        html.Div(
            PageHeader(
                "Entrada de Dados",
                "Importação de dados de produção e manejo — acompanhamento do processamento inicial.",
                ctx.global_filter,
                filter_options,
                cycle=active if active.get("cycle_id") else None,
            ),
            id="de-farm-existing-header",
            style=existing_style,
        ),
        html.Div(
            AlertBox(
                "Selecione uma fazenda existente no filtro global ou use a aba Cadastrar nova fazenda.",
                variant="info",
                className="small mb-3",
            ) if ctx.no_farm_selected else None,
            id="de-farm-existing-alert",
            style=existing_style,
        ),
        FarmSelector(ctx, filter_options),
        dbc.Card(dbc.CardBody([
            SectionHeader(
                "Importar arquivo",
                "Informe o período e o layout do CSV, depois selecione o arquivo.",
            ),
            html.Div([
                *RawUploadForm(
                    upload_cycle_props,
                    upload_filter,
                    filter_options,
                    show_hash=False,
                    mode="managerial",
                ),
                _render_upload_feedback(upload_feedback),
            ], className="upload-zone-wrapper"),
        ]), className="agro-card mb-3", id="de-farm-upload-section"),
        html.Div(_context_block(ctx), id="de-farm-context-section", style=existing_style),
        html.Div(
            _build_monitoring_section(ctx, cycles, context_cycle_id),
            id="de-farm-monitoring-section",
            style=existing_style,
        ),
    ]

    return html.Div(body, className="page-data-entry page-content-inner")
