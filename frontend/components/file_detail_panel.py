"""Painel de detalhes do arquivo selecionado — Entrada de Dados."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.agro_tabs import AgroTabs
from components.cards import AlertBox, SectionHeader
from components.compact_file_stepper import CompactFileStepper
from components.hash_viewer import HashViewer
from components.key_value_table import KeyValueTable
from components.tables import DataTable
from services.cycle_status_service import resolve_managerial_status
from services.data_view_service import (
    build_data_quality_view,
    build_file_events_view,
    build_file_select_options,
    build_raw_data_view,
    build_wrapper_view,
)


def _summary_tab(cycle: dict) -> list:
    raw = build_raw_data_view(cycle) if cycle.get("raw_file") else {}
    st = resolve_managerial_status(cycle)
    return [
        KeyValueTable({
            "Arquivo": raw.get("filename", "—"),
            "Fazenda": cycle.get("property_name", "—"),
            "Período": raw.get("period") or cycle.get("reporting_period", "—"),
            "Layout/tipo": cycle.get("layout_id", "—"),
            "Data de envio": raw.get("uploaded_at") or cycle.get("created_at", "—"),
            "Status atual": st.label,
            "Próxima ação": st.next_action or "—",
        }),
    ]


def _pipeline_tab(cycle: dict) -> list:
    return [CompactFileStepper(cycle)]


def _quality_tab(cycle: dict) -> list:
    if not cycle.get("wrapper"):
        return [html.P("Qualidade disponível após normalização do arquivo.", className="text-aux small")]
    quality = build_data_quality_view(cycle)
    wrapper = build_wrapper_view(cycle)
    warnings = quality.get("warnings") or []
    errors = quality.get("errors") or []
    missing = quality.get("missing_fields") or []
    children: list = [
        KeyValueTable({
            "Taxa válidos (%)": quality.get("valid_rate_pct"),
            "Taxa rejeição (%)": quality.get("rejection_rate_pct"),
            "Linhas lidas": wrapper.get("rows_read", 0),
            "Linhas válidas": wrapper.get("rows_valid", 0),
            "Erros críticos": quality.get("critical_errors", 0),
        }),
    ]
    if missing:
        children.append(html.Div([
            html.Strong("Campos ausentes", className="small d-block mt--2 mb-1"),
            html.Ul([html.Li(str(m), className="small") for m in missing[:10]], className="mb-2"),
        ]))
    if warnings:
        children.append(html.Div([
            html.Strong("Alertas de validação", className="small d-block mb-1"),
            html.Ul([html.Li(str(w), className="small text-aux") for w in warnings[:8]], className="mb-2"),
        ]))
    if errors:
        children.append(html.Div([
            html.Strong("Erros de estrutura", className="small d-block mb-1"),
            html.Ul([html.Li(str(e), className="small") for e in errors[:8]], className="mb-2"),
        ]))
    if not warnings and not errors and not quality.get("critical_errors"):
        children.append(AlertBox("Nenhum alerta crítico identificado.", variant="success", className="small"))
    return children


def _hash_tab(cycle: dict) -> list:
    raw = build_raw_data_view(cycle) if cycle.get("raw_file") else {}
    if not raw.get("sha256"):
        return [html.P("Nenhum hash registrado para este arquivo.", className="empty-state small")]
    norm_path = "—"
    norm = cycle.get("normalized_data")
    if isinstance(norm, list) and norm and isinstance(norm[0], dict):
        norm_path = norm[0].get("stored_path") or norm[0].get("source", "—")
    elif cycle.get("wrapper"):
        norm_path = (cycle.get("wrapper") or {}).get("output_path", "—")
    return [
        HashViewer({"SHA-256 (arquivo original)": raw.get("sha256", "")}),
        KeyValueTable({
            "Local do arquivo original": raw.get("stored_path", "—"),
            "Local do arquivo normalizado": norm_path,
            "Data/hora da preservação": raw.get("uploaded_at") or cycle.get("created_at", "—"),
        }),
    ]


def _events_tab(cycle: dict) -> list:
    events = build_file_events_view(cycle)
    if not events:
        return [html.P("Nenhum evento registrado para este arquivo.", className="empty-state small")]
    return [
        html.P(
            "Resumo dos eventos principais do processamento inicial. "
            "Para auditoria completa, consulte Auditoria Técnica.",
            className="text-aux small mb-2",
        ),
        DataTable(events, columns=["evento", "etapa", "status", "data"], page_size=8),
    ]


def FileDetailPanel(
    cycle: dict | None,
    *,
    cycles: list[dict] | None = None,
    selected_cycle_id: str | None = None,
) -> dbc.Card:
    """Painel lateral com abas de detalhes do arquivo/ciclo selecionado."""
    all_cycles = cycles or []
    options = build_file_select_options(all_cycles) if all_cycles else []

    if not cycle or not cycle.get("cycle_id"):
        return dbc.Card(dbc.CardBody([
            SectionHeader("Detalhes do arquivo"),
            html.Div(
                "Selecione um arquivo na tabela ou envie um novo CSV para ver os detalhes.",
                className="empty-state-card empty-state small",
            ),
        ]), className="agro-card h-100 file-detail-panel")

    raw = build_raw_data_view(cycle) if cycle.get("raw_file") else {}
    st = resolve_managerial_status(cycle)

    tabs = [
        dbc.Tab(_summary_tab(cycle), label="Resumo", tab_id="fd-summary"),
        dbc.Tab(_pipeline_tab(cycle), label="Pipeline", tab_id="fd-pipeline"),
        dbc.Tab(_quality_tab(cycle), label="Qualidade", tab_id="fd-quality"),
        dbc.Tab(_hash_tab(cycle), label="Hash e armazenamento", tab_id="fd-hash"),
        dbc.Tab(_events_tab(cycle), label="Eventos", tab_id="fd-events"),
    ]

    header = [
        SectionHeader("Detalhes do arquivo", "Todos os arquivos carregados para esta fazenda, incluindo os com erro."),
        html.Small("Arquivo", className="gf-label d-block"),
        dbc.Select(
            id="data-entry-file-select",
            options=options,
            value=selected_cycle_id or cycle.get("cycle_id"),
            size="sm",
            className="form-select-narrow mb-2",
        ),
        html.Span(st.label, className=f"badge-status badge-status-{st.variant} me-1"),
    ]

    return dbc.Card(dbc.CardBody([
        html.Div(header, className="mb-3"),
        AgroTabs(tabs, active_tab="fd-summary"),
    ]), className="agro-card h-100 file-detail-panel")
