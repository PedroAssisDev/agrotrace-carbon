"""Entrada de Dados — upload e pipeline automática gerencial."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.auto_pipeline_progress import AutoPipelineProgressBanner
from components.cards import AlertBox, SectionHeader
from components.cycle_status_timeline import CycleStatusTimeline
from components.empty_state import EmptyFilterState
from components.key_value_table import KeyValueTable
from components.managerial_status import ApprovalStatusBadge, CycleStatusChip
from components.page_header import PageHeader
from components.upload_form import RawUploadForm
from services.cycle_status_service import resolve_managerial_status
from services.data_view_service import build_data_quality_view, build_raw_data_view
from services.page_context import resolve_page_context


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    ctx = resolve_page_context(cycle, global_filter, context_cycle_id)
    c = ctx.active_cycle
    st = resolve_managerial_status(c)

    body = [
        PageHeader(
            "Entrada de Dados",
            "Importação de dados de produção e manejo — processamento automático até revisão humana.",
            ctx.global_filter,
            filter_options,
            cycle=c,
        ),
    ]

    if ctx.is_empty and not c.get("cycle_id"):
        body.append(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
        if not ctx.no_farm_selected and not ctx.no_farm_cycles:
            body.append(dbc.Card(dbc.CardBody(RawUploadForm(c or {}, ctx.global_filter, filter_options)), className="agro-card mt-3"))
        return html.Div(body, className="page-data-entry page-content-inner")

    raw = build_raw_data_view(c) if c.get("raw_file") else {}
    quality = build_data_quality_view(c) if c.get("wrapper") else {}
    progress_banner = AutoPipelineProgressBanner(c)

    next_steps = []
    if st.key == "pending_approval":
        next_steps.append(AlertBox(
            "Processamento concluído. O resultado preliminar aguarda aprovação humana em Revisão e Aprovação.",
            variant="pending",
            className="small",
        ))
        next_steps.append(dbc.Button("Ir para Revisão e Aprovação", href="/approval", size="sm", className="btn-agro-primary mb-3"))
    elif st.next_action and st.key not in ("pending_approval", "published", "evidence_generated", "integrity_verified"):
        next_steps.append(AlertBox(st.next_action, variant="info", className="small"))

    body.extend([
        CycleStatusChip(c),
        CycleStatusTimeline(c),
        progress_banner,
        dbc.Card(dbc.CardBody([
            SectionHeader("Importar arquivo"),
            dcc.Loading(
                html.Div(RawUploadForm(c, ctx.global_filter, filter_options), className="upload-zone-wrapper"),
                type="default",
                color="#2d6a4f",
            ),
        ]), className="agro-card mb-3"),
    ])

    if raw:
        body.append(dbc.Card(dbc.CardBody([
            SectionHeader("Resumo do arquivo"),
            KeyValueTable({
                "Arquivo": raw.get("filename"),
                "Período": raw.get("period"),
                "Status": st.label,
                "Hash preliminar": (c.get("calculation") or {}).get("preliminary_hash", "—"),
            }),
            html.A("Detalhes técnicos → Auditoria Técnica", href="/technical-audit", className="small"),
        ]), className="agro-card mb-3"))

    if quality and c.get("wrapper"):
        body.append(dbc.Card(dbc.CardBody([
            SectionHeader("Qualidade resumida"),
            KeyValueTable({
                "Taxa válidos (%)": quality.get("valid_rate_pct"),
                "Alertas": len(quality.get("warnings") or []),
                "Erros críticos": quality.get("critical_errors", 0),
            }),
        ]), className="agro-card mb-3"))

    body.extend(next_steps)
    return html.Div(body, className="page-data-entry page-content-inner")
