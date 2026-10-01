"""Callbacks da Auditoria Técnica — inspeção, filtros locais e integridade."""

from __future__ import annotations

import base64
import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html, no_update

from components.audit.audit_integrity_panel import AuditIntegrityPanel
from components.audit.audit_payload_viewer import AuditPayloadViewer
from components.payload_viewer import PayloadViewer
from services import blockchain_adapter, provenance_adapter, save_file_adapter
from services.audit_event_service import (
    filter_events_for_ui,
    most_recent_event,
    resolve_cycle_events,
)
from services.audit_payload_service import resolve_payload
from pages.technical_audit import _chrome_children
from pages.technical_audit_sections import build_audit_tab
from services.page_context import resolve_page_context
from utils.hash_helpers import truncate_hash
from utils.sanitize import safe_error_message

logger = logging.getLogger("agrotrace.technical_audit")


def _ctx_from_stores(cycle_data, global_filter, context_cycle_id):
    return resolve_page_context(cycle_data, global_filter, context_cycle_id)


def _load_events(ctx):
    prov_cycle_id = ctx.cycle_id or ctx.active_cycle.get("cycle_id") or ""
    all_events = provenance_adapter.list_events_for_context(
        ctx.global_filter,
        ctx.all_cycles,
        ctx.active_cycle,
        context_cycle_id=prov_cycle_id,
        prov_cycle_id=prov_cycle_id or None,
        cycles_in_context=ctx.cycles,
    )
    resolved = resolve_cycle_events(all_events, ctx.active_cycle, include_global_fallback=False)
    events = resolved["cycle_events"]
    if not events and ctx.active_cycle.get("provenance_events"):
        from services.provenance_view_service import enrich_events
        events = enrich_events(ctx.active_cycle.get("provenance_events") or [])
    return events, resolved


@callback(
    Output("ta-page-header", "children"),
    Output("ta-empty-state", "children"),
    Output("ta-cycle-select-row", "children"),
    Input("global-filter-store", "data"),
    Input("cycle-store", "data"),
    Input("context-cycle-id", "data"),
    State("url", "pathname"),
    State("filter-options-store", "data"),
    prevent_initial_call=False,
)
def refresh_technical_audit_chrome(
    global_filter, cycle_data, context_cycle_id, pathname, filter_options,
):
    """Atualiza cabeçalho/seletor sem remontar abas (evita race no React)."""
    if (pathname or "/") != "/technical-audit":
        return no_update, no_update, no_update
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    header, empty, cycle_row = _chrome_children(ctx_obj, filter_options)
    return header, empty, cycle_row


@callback(
    Output("ta-integrity-panel", "children"),
    Input("verify-cycle-select", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def update_integrity_panel(selected_cycle_id, cycle_data, global_filter, context_cycle_id):
    """Atualiza painel somente ao trocar ciclo no select da aba Integridade."""
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    cycle = ctx_obj.active_cycle
    if not cycle.get("cycle_id"):
        return no_update

    from pages.technical_audit_sections import (
        _cycles_for_evidence_scope,
        _default_verify_cycle_id,
    )

    pkg_options = blockchain_adapter.build_verify_cycle_options(
        _cycles_for_evidence_scope(ctx_obj),
    )
    if not pkg_options:
        return html.Div(
            "Nenhum pacote de evidências no escopo. Blockchain pode estar bloqueado "
            "ou o ciclo ainda não foi publicado.",
            className="empty-state",
        )

    sel = selected_cycle_id or _default_verify_cycle_id(cycle, pkg_options)
    return AuditIntegrityPanel(cycle, pkg_options, selected_cycle_id=sel)


@callback(
    Output("ta-prov-events-body", "children"),
    Input("ta-prov-phase", "value"),
    Input("ta-prov-service", "value"),
    Input("ta-prov-status", "value"),
    Input("ta-prov-event-type", "value"),
    Input("ta-prov-search", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def filter_provenance_events(
    phase, service, status, event_type, search, cycle_data, global_filter, context_cycle_id,
):
    """Atualiza só tabela/timeline — filtros permanecem montados (valores preservados)."""
    from components.audit.audit_event_explorer import _events_body

    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    if not ctx_obj.active_cycle.get("cycle_id"):
        return no_update

    events, _resolved = _load_events(ctx_obj)
    filtered = filter_events_for_ui(
        events,
        phase=phase,
        service=service,
        status=status,
        event_type=event_type,
        search=search,
    )
    body = _events_body(filtered)
    return body.children


@callback(
    Output("ta-payload-event-view", "children"),
    Input("ta-prov-events-table", "selected_rows"),
    Input("ta-prov-events-table", "data"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def show_selected_event_payload(
    selected_rows, table_data, cycle_data, global_filter, context_cycle_id,
):
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    events, _ = _load_events(ctx_obj)

    if not events:
        return PayloadViewer(None, title="Nenhum evento")

    evt = None
    if selected_rows and table_data:
        idx = selected_rows[0]
        if 0 <= idx < len(table_data):
            row = table_data[idx]
            event_type = row.get("evento")
            created = row.get("data")
            for e in events:
                if e.get("event_type") == event_type and e.get("created_at") == created:
                    evt = e
                    break
            if not evt and 0 <= idx < len(events):
                evt = events[idx]

    if not evt:
        evt = most_recent_event(events)

    if not evt:
        return PayloadViewer(None, title="Nenhum evento")

    return PayloadViewer(
        evt.get("payload_json") or evt.get("payload"),
        title=f"{evt.get('event_type', 'Evento')} — {evt.get('created_at', '—')}",
    )


@callback(
    Output("ta-payload-content", "children"),
    Input("ta-payload-source", "value"),
    Input("ta-prov-events-table", "selected_rows"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def update_payload_content(
    source, selected_rows, cycle_data, global_filter, context_cycle_id,
):
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    cycle = ctx_obj.active_cycle
    if not cycle.get("cycle_id"):
        return no_update

    events, _ = _load_events(ctx_obj)
    selected_event = None
    if selected_rows and events:
        idx = selected_rows[0]
        if 0 <= idx < len(events):
            selected_event = events[idx]
        else:
            selected_event = most_recent_event(events)
    elif source == "event":
        selected_event = most_recent_event(events)

    result = resolve_payload(
        source or "cycle",
        cycle,
        selected_event=selected_event,
        events=events,
    )
    return AuditPayloadViewer(result, content_only=True)


@callback(
    Output("ta-tab-content", "children"),
    Input("technical-audit-tabs", "active_tab"),
    Input("global-filter-store", "data"),
    Input("cycle-store", "data"),
    Input("context-cycle-id", "data"),
    State("url", "pathname"),
    prevent_initial_call=False,
)
def render_technical_audit_tab(
    active_tab, global_filter, cycle_data, context_cycle_id, pathname,
):
    """Único callback que remonta o conteúdo da aba ativa."""
    if (pathname or "/") != "/technical-audit":
        return no_update
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    return build_audit_tab(active_tab, ctx_obj)


@callback(
    Output("ta-active-tab-store", "data"),
    Input("technical-audit-tabs", "active_tab"),
    prevent_initial_call=True,
)
def persist_technical_audit_tab(active_tab):
    """Persiste aba ativa entre navegações."""
    return active_tab or "ta-summary"


@callback(
    Output("ta-raw-verify-result", "children"),
    Output("ta-raw-verify-store", "data"),
    Input("ta-raw-verify-btn", "n_clicks"),
    State("ta-raw-artifact-select", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def verify_raw_artifact(n_clicks, selected, cycle_data, global_filter, context_cycle_id):
    """Verifica integridade do bruto via adapter (sem lógica de storage na UI)."""
    if not n_clicks:
        return no_update, no_update
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    cycle_id = ctx_obj.active_cycle.get("cycle_id")
    if not cycle_id:
        return dbc.Alert("Nenhum ciclo ativo.", color="warning", className="mb-0"), None

    try:
        if selected:
            try:
                retrieved = save_file_adapter.retrieve_original(artifact_id=str(selected))
            except Exception:
                retrieved = save_file_adapter.retrieve_by_cycle_id(str(cycle_id))
        else:
            retrieved = save_file_adapter.retrieve_by_cycle_id(str(cycle_id))
        dto = save_file_adapter.to_ui_dto(retrieved)
        alert = dbc.Alert(
            [
                html.Strong("Integridade verificada. "),
                html.Span(
                    f"Hash registrado {truncate_hash(dto.get('registered_sha256') or '', 16)} "
                    f"= recalculado {truncate_hash(dto.get('recomputed_sha256') or '', 16)}."
                ),
            ],
            color="success",
            className="mb-0",
        )
        return alert, dto
    except Exception as exc:  # noqa: BLE001 — exibir erro de domínio na UI
        logger.warning("verify_raw_artifact failed: %s", exc)
        return dbc.Alert(safe_error_message(exc), color="danger", className="mb-0"), None


@callback(
    Output("ta-raw-download", "data"),
    Input("ta-raw-download-btn", "n_clicks"),
    State("ta-raw-artifact-select", "value"),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("context-cycle-id", "data"),
    prevent_initial_call=True,
)
def download_raw_artifact(n_clicks, selected, cycle_data, global_filter, context_cycle_id):
    """Baixa cópia do original via adapter; filename = nome original (sem path)."""
    if not n_clicks:
        return no_update
    ctx_obj = _ctx_from_stores(cycle_data, global_filter, context_cycle_id)
    cycle_id = ctx_obj.active_cycle.get("cycle_id")
    if not cycle_id:
        return no_update

    try:
        if selected:
            try:
                retrieved = save_file_adapter.retrieve_original(artifact_id=str(selected))
            except Exception:
                retrieved = save_file_adapter.retrieve_by_cycle_id(str(cycle_id))
        else:
            retrieved = save_file_adapter.retrieve_by_cycle_id(str(cycle_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("download_raw_artifact failed: %s", exc)
        return no_update

    content = retrieved.get("content") or b""
    if isinstance(content, str):
        content = content.encode("utf-8")
    filename = retrieved.get("original_filename") or "original.bin"
    return dict(
        content=base64.b64encode(content).decode("ascii"),
        filename=filename,
        base64=True,
        type=retrieved.get("content_type") or "application/octet-stream",
    )


def register(_app) -> None:
    pass
