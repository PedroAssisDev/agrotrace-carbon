"""Seções da Auditoria Técnica — auditoria e rastreabilidade."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.audit import (
    AuditArtifactTable,
    AuditBlockchainGate,
    AuditComplianceMatrix,
    AuditEventExplorer,
    AuditIntegrityPanel,
    AuditLogPanel,
    AuditPayloadViewer,
    AuditSummaryCards,
    AuditTimeline,
    ProvenanceSqlWorkspace,
    RawArtifactPanel,
    TechnicalActionsPanel,
)
from components.empty_state import EmptyFilterState
from components.payload_viewer import PayloadViewer
from services import blockchain_adapter, provenance_adapter
from services.audit_artifact_service import build_artifact_rows, group_artifacts
from services.audit_event_service import (
    most_recent_event,
    resolve_cycle_events,
    unique_filter_options,
)
from services.audit_payload_service import resolve_payload
from services.audit_summary_service import build_audit_summary, detect_integration_mode
from services.audit_timeline_service import build_audit_timeline
from services.blockchain_view_service import blockchain_lock_message, is_blockchain_unlocked
from services.page_context import PageContext
from services.provenance_schema_service import get_audit_schema
from services.provenance_view_service import build_derivation_graph


def _empty(ctx: PageContext) -> html.Div:
    return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))


def _cycle_header(ctx: PageContext) -> list:
    """Seletor de ciclo fica no shell da página (`technical_audit.layout`)."""
    return []


def build_summary_section(ctx: PageContext) -> html.Div:
    if not ctx.active_cycle.get("cycle_id"):
        return _empty(ctx)
    summary = build_audit_summary(ctx)
    cycle = ctx.active_cycle
    from components.tables import DataTable

    chain_rows: list[dict] = []
    try:
        from services.blockchain_linkage_view_service import build_linkage_rows, build_linkage_trail

        trail = build_linkage_trail(cycle)
        chain_rows = build_linkage_rows(trail)
        chain_block = html.Div([
            html.H6("Cadeia de auditoria", className="mt-3 mb-2"),
            html.P(
                "Resultado → publicação → pacote → solicitação → transação → verificação "
                "(+ histórico de correção quando existir).",
                className="text-muted small",
            ),
            DataTable(chain_rows, columns=["etapa", "identificador", "presente"])
            if chain_rows
            else html.P("Sem vínculos ainda.", className="text-muted small"),
            html.P(
                f"Versões de resultado: {len(cycle.get('result_versions') or [])} · "
                f"Correções: {len(cycle.get('corrections') or [])}",
                className="small mt-2",
            ),
            html.P(
                f"Explicação do cálculo: "
                f"{'presente' if (cycle.get('calculation') or {}).get('explanation') else 'ausente'}",
                className="small",
            ),
        ])
    except Exception as exc:
        from utils.sanitize import safe_error_message

        chain_block = dbc.Alert(f"Cadeia indisponível: {safe_error_message(exc)}", color="warning", className="mt-3")

    vm = cycle.get("version_manifest")
    if not vm:
        try:
            from services.version_manifest_service import build_version_manifest

            vm = build_version_manifest(cycle).to_dict()
        except Exception:
            vm = None
    vm_rows = []
    if isinstance(vm, dict):
        for key in (
            "layout_id",
            "layout_version",
            "ontology_version",
            "method_code",
            "method_version",
            "canonicalization_strategy",
            "blockchain_contract_version",
            "abi_version",
            "evidence_schema_version",
        ):
            entry = vm.get(key) or {}
            val = entry.get("value") if isinstance(entry, dict) else entry
            reason = entry.get("missing_reason") if isinstance(entry, dict) else None
            vm_rows.append({
                "campo": key,
                "valor": str(val) if val is not None else "—",
                "motivo": reason or "",
            })
    vm_block = html.Div([
        html.H6("VersionManifest (RNF010)", className="mt-3 mb-2"),
        DataTable(vm_rows, columns=["campo", "valor", "motivo"])
        if vm_rows
        else html.P("Manifesto de versões indisponível.", className="text-muted small"),
        html.P(
            f"Hash do manifesto: {(vm or {}).get('manifest_hash') or '—'} · "
            f"Conflitos: {len((vm or {}).get('consistency_conflicts') or [])}",
            className="small text-aux",
        ),
    ]) if vm is not None else html.Div()

    return html.Div([
        *_cycle_header(ctx),
        AuditSummaryCards(
            summary["cards"],
            main_message=summary.get("main_message"),
            banners=summary.get("banners"),
        ),
        html.Hr(className="my-4"),
        AuditComplianceMatrix((summary.get("compliance") or {}).get("matrix") or []),
        chain_block,
        vm_block,
        TechnicalActionsPanel(),
    ])


def build_timeline_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)
    mode = detect_integration_mode(cycle)
    return html.Div([
        *_cycle_header(ctx),
        AuditTimeline(build_audit_timeline(cycle), integration_mode=mode),
    ])


def _load_provenance_events(ctx: PageContext) -> dict:
    prov_cycle_id = ctx.cycle_id or ctx.active_cycle.get("cycle_id") or ""
    all_events = provenance_adapter.list_events_for_context(
        ctx.global_filter,
        ctx.all_cycles,
        ctx.active_cycle,
        context_cycle_id=prov_cycle_id,
        prov_cycle_id=prov_cycle_id or None,
        cycles_in_context=ctx.cycles,
    )
    return resolve_cycle_events(all_events, ctx.active_cycle, include_global_fallback=False)


def build_provenance_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)

    resolved = _load_provenance_events(ctx)
    events = resolved["cycle_events"]
    if not events and not resolved["has_cycle_match"]:
        cycle_prov = cycle.get("provenance_events") or []
        if cycle_prov:
            from services.provenance_view_service import enrich_events
            events = enrich_events(cycle_prov)

    filter_opts = unique_filter_options(events)
    recent = most_recent_event(events)

    return html.Div([
        *_cycle_header(ctx),
        html.Div(id="ta-event-explorer", children=AuditEventExplorer(
            events,
            filter_opts,
            show_global_warning=not resolved["has_cycle_match"] and not events,
        )),
        html.Hr(className="my-3"),
        html.H6("Derivação", className="section-subtitle"),
        html.Ul(
            [html.Li(f"{e['from']} → {e['to']}") for e in build_derivation_graph(events)],
            className="derivation-timeline mt-2",
        ) if events else html.P("Sem derivação.", className="text-muted small"),
        html.Hr(className="my-3"),
        html.H6("Payload do evento", className="section-subtitle"),
        html.P(
            "Evento mais recente por timestamp (selecione na tabela para outro evento).",
            className="text-aux small mb-2",
        ),
        html.Div(id="ta-payload-event-view", children=(
            PayloadViewer(recent.get("payload_json") or recent.get("payload"), title=recent.get("event_type", "Evento"))
            if recent else html.P("Nenhum evento disponível.", className="text-muted small")
        )),
    ])


def build_provenance_queries_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)
    schema = get_audit_schema()
    return html.Div([
        *_cycle_header(ctx),
        ProvenanceSqlWorkspace(ctx, schema),
    ])


def build_artifacts_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)
    rows = build_artifact_rows(cycle)
    grouped = group_artifacts(rows)
    mode = detect_integration_mode(cycle)
    return html.Div([
        *_cycle_header(ctx),
        RawArtifactPanel(cycle),
        AuditArtifactTable(grouped, integration_mode=mode),
    ])


def _cycles_for_evidence_scope(ctx: PageContext) -> list[dict]:
    """Ciclos do escopo + ciclo ativo (mesmo se filtrado pelo data_mode)."""
    by_id: dict[str, dict] = {}
    for c in list(ctx.cycles or []) + list(ctx.analysis_cycles or []):
        cid = c.get("cycle_id")
        if cid:
            by_id[cid] = c
    active = ctx.active_cycle or {}
    active_id = active.get("cycle_id")
    if active_id:
        by_id.setdefault(active_id, active)
    return list(by_id.values())


def _default_verify_cycle_id(cycle: dict, pkg_options: list[dict]) -> str | None:
    """Prefere ciclo ativo se tiver pacote; senão o primeiro com evidência."""
    if not pkg_options:
        return None
    values = {opt.get("value") for opt in pkg_options}
    active_id = cycle.get("cycle_id")
    if active_id in values:
        return active_id
    return pkg_options[0].get("value")


def _is_sepolia_anchored(cycle: dict) -> bool:
    anchoring = cycle.get("anchoring") or {}
    evidence = cycle.get("evidence_package") or {}
    network = anchoring.get("network") or evidence.get("network")
    kind = anchoring.get("anchoring_kind") or ""
    if network != "ethereum_sepolia" or kind == "SIMULADA":
        return False
    tx = str(anchoring.get("transaction_id") or evidence.get("transaction_id") or "")
    return bool(anchoring.get("explorer_url")) or (tx.startswith("0x") and len(tx) >= 66)


def _default_blockchain_cycle_id(cycle: dict, scope_cycles: list[dict], pkg_options: list[dict]) -> str | None:
    """Ativo com pacote → Sepolia no escopo → primeiro com pacote."""
    if not pkg_options:
        return None
    values = {opt.get("value") for opt in pkg_options}
    active_id = cycle.get("cycle_id")
    if active_id in values and (cycle.get("evidence_package") or {}).get("evidence_package_id"):
        # Se o ativo só tem simulação, preferir Sepolia no escopo quando existir
        if _is_sepolia_anchored(cycle):
            return active_id
        for c in scope_cycles:
            cid = c.get("cycle_id")
            if cid in values and _is_sepolia_anchored(c):
                return cid
        return active_id
    for c in scope_cycles:
        cid = c.get("cycle_id")
        if cid in values and _is_sepolia_anchored(c):
            return cid
    return pkg_options[0].get("value")


def build_blockchain_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)

    scope_cycles = _cycles_for_evidence_scope(ctx)
    # Garante dados completos (ancoring/explorer) ao montar opções
    from utils.file_helpers import get_cycle

    hydrated: list[dict] = []
    for c in scope_cycles:
        cid = c.get("cycle_id")
        full = get_cycle(cid) if cid else None
        hydrated.append(full or c)

    pkg_options = blockchain_adapter.build_verify_cycle_options(hydrated)
    selected_id = _default_blockchain_cycle_id(cycle, hydrated, pkg_options)
    display = cycle
    if selected_id and selected_id != cycle.get("cycle_id"):
        loaded = get_cycle(selected_id)
        if loaded:
            display = loaded

    unlocked = is_blockchain_unlocked(display)
    approval = (display.get("approval") or {}).get("decision", "Pendente")
    approval_label = "Concluída" if approval == "APPROVED" else "Pendente"
    pub_st = (display.get("steps") or {}).get("publication", {}).get("status", "PENDING")
    pub_label = "Concluída" if pub_st in {"DONE", "DONE_WARNINGS"} else "Pendente"
    pkg_rows = blockchain_adapter.build_package_summary_rows(hydrated)

    panel = AuditBlockchainGate(
        display,
        unlocked=unlocked,
        lock_message=blockchain_lock_message(display) or "",
        approval_status=approval_label,
        publication_status=pub_label,
        pkg_rows=pkg_rows if unlocked else [],
        scoped_package_count=len(pkg_rows),
        pkg_options=pkg_options,
        selected_cycle_id=selected_id,
    )

    return html.Div([
        *_cycle_header(ctx),
        html.Div(id="ta-blockchain-panel", children=panel),
    ])


def build_integrity_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)

    pkg_options = blockchain_adapter.build_verify_cycle_options(_cycles_for_evidence_scope(ctx))
    selected_id = _default_verify_cycle_id(cycle, pkg_options)
    panel = (
        AuditIntegrityPanel(cycle, pkg_options, selected_cycle_id=selected_id)
        if pkg_options
        else html.Div(
            "Nenhum pacote de evidências no escopo. Blockchain pode estar bloqueado "
            "ou o ciclo ainda não foi publicado.",
            className="empty-state",
        )
    )

    return html.Div([
        *_cycle_header(ctx),
        html.Div(id="ta-integrity-panel", children=panel),
    ])


def build_logs_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)

    errors = cycle.get("errors") or []
    warnings = cycle.get("warnings") or []
    resolved = _load_provenance_events(ctx)
    events = resolved["cycle_events"][:50]

    def _row(sev, origem, msg, etapa, ts, det=""):
        return {"severidade": sev, "origem": origem, "mensagem": msg, "etapa": etapa, "timestamp": ts, "detalhe": det}

    err_rows = [_row("Erro", "ciclo", e.get("message", ""), e.get("step", "—"), "—") for e in errors if isinstance(e, dict)]
    warn_rows = [_row("Alerta", "ciclo", w.get("message", ""), w.get("step", "—"), "—") for w in warnings if isinstance(w, dict)]
    ev_rows = [_row("Info", "proveniência", e.get("event_type", ""), e.get("phase", "—"), e.get("created_at", "—")) for e in events]

    mock_count = 0
    for step in (cycle.get("steps") or {}).values():
        if step.get("mode") == "mock" or step.get("fallback_reason"):
            mock_count += 1
    for key in ("evidence_package", "anchoring", "integrity"):
        if (cycle.get(key) or {}).get("mode") == "mock":
            mock_count += 1

    filter_rows = []
    from services.audit_summary_service import build_consistency_banners
    for b in build_consistency_banners(ctx):
        filter_rows.append(_row("Atenção", "filtro", b.get("message", ""), b.get("title", "—"), "—"))

    log_data = {
        "summary": {
            "errors": len(err_rows),
            "warnings": len(warn_rows),
            "mock_fallbacks": mock_count,
            "no_match": 0 if resolved["has_cycle_match"] else 1,
            "events": len(ev_rows),
        },
        "sections": {
            "cycle_errors": err_rows,
            "cycle_warnings": warn_rows,
            "provenance_events": ev_rows,
            "filter_inconsistencies": filter_rows,
        },
        "rows": err_rows + warn_rows + ev_rows + filter_rows,
    }

    return html.Div([
        *_cycle_header(ctx),
        AuditLogPanel(log_data),
    ])


def build_payload_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return _empty(ctx)

    resolved = _load_provenance_events(ctx)
    initial = resolve_payload("cycle", cycle, events=resolved["cycle_events"])

    return html.Div([
        *_cycle_header(ctx),
        html.Div(id="ta-payload-view", children=AuditPayloadViewer(initial, show_selector=True)),
    ])


_AUDIT_TAB_BUILDERS = {
    "ta-summary": build_summary_section,
    "ta-timeline": build_timeline_section,
    "ta-provenance": build_provenance_section,
    "ta-prov-queries": build_provenance_queries_section,
    "ta-artifacts": build_artifacts_section,
    "ta-blockchain": build_blockchain_section,
    "ta-integrity": build_integrity_section,
    "ta-logs": build_logs_section,
    "ta-payload": build_payload_section,
}


def build_audit_tab(tab_id: str | None, ctx: PageContext) -> html.Div:
    """Renderiza uma aba da Auditoria Técnica pelo id."""
    builder = _AUDIT_TAB_BUILDERS.get(tab_id or "ta-summary", build_summary_section)
    try:
        return builder(ctx)
    except Exception as exc:
        from utils.sanitize import safe_error_message

        return html.Div(
            dbc.Alert(
                f"Erro ao carregar a aba {tab_id or 'ta-summary'}: {safe_error_message(exc)}",
                color="danger",
            ),
            className="pt-2",
        )
