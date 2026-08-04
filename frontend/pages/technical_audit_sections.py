"""Seções embutidas da Auditoria Técnica."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.blockchain_anchor_card import BlockchainAnchorCard
from components.cards import AlertBox
from components.empty_state import EMPTY_BLOCKCHAIN_LOCKED, EmptyFilterState, EmptyState
from components.evidence_package_viewer import EvidencePackageViewer
from components.hash_viewer import HashViewer
from components.integrity_comparison_table import IntegrityComparisonTable
from components.key_value_table import KeyValueTable
from components.merkle_tree import MerkleTreeView
from components.mode_badge import ModeBadge
from components.ontology_graph import OntologyGraphViewer
from components.payload_viewer import PayloadViewer
from components.provenance_timeline import ProvenanceTimeline
from components.tables import DataTable
from services import blockchain_adapter, provenance_adapter
from services.blockchain_view_service import build_evidence_summary, blockchain_lock_message, is_blockchain_unlocked
from services.cycle_state import events_for_step
from services.data_view_service import (
    build_data_quality_view,
    build_normalized_table_rows,
    build_raw_data_view,
    build_wrapper_view,
)
from services.integrity_view_service import build_integrity_summary, integrity_message
from services.page_context import PageContext
from services.provenance_view_service import build_derivation_graph, enrich_events


def build_data_section(ctx: PageContext) -> html.Div:
    c = ctx.active_cycle
    if not c.get("cycle_id"):
        return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
    raw = build_raw_data_view(c)
    wrapper = build_wrapper_view(c)
    norm_rows = build_normalized_table_rows(c)
    quality = build_data_quality_view(c)
    return html.Div(dbc.Tabs([
        dbc.Tab(label="Dado Bruto", children=html.Div([KeyValueTable(raw), HashViewer({"raw": raw.get("sha256")})], className="mt-3")),
        dbc.Tab(label="Arquivo Original", children=html.Div(KeyValueTable({"caminho": raw.get("stored_path"), "hash": raw.get("sha256")}), className="mt-3")),
        dbc.Tab(label="Wrapper", children=html.Div(KeyValueTable(wrapper), className="mt-3")),
        dbc.Tab(label="Dado Normalizado", children=html.Div(
            DataTable(norm_rows, columns=["variavel", "valor", "unidade", "periodo", "status"] if norm_rows else []),
            className="mt-3",
        )),
        dbc.Tab(label="Qualidade dos Dados", children=html.Div(KeyValueTable(quality), className="mt-3")),
    ], className="agro-tabs"))


def build_ontology_section(ctx: PageContext) -> html.Div:
    c = ctx.active_cycle
    if not c.get("cycle_id"):
        return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
    ont = c.get("ontology") or {}
    sem = c.get("semantic_validation") or {}
    canonical = {
        "canonical_dataset_id": ont.get("canonical_dataset_id", "—"),
        "ontology_version": ont.get("ontology_version"),
        "entities_created": ont.get("entities_created", 0),
        "dataset_hash": ont.get("dataset_hash", "—"),
    }
    validation = {
        "rules_executed": sem.get("total_validations", 0),
        "critical_errors": sem.get("critical_errors", 0),
        "warnings": sem.get("warnings", 0),
    }
    nodes = ont.get("graph_nodes")
    edges = ont.get("graph_edges")
    inference_lis = _inference_list_items(sem)
    return html.Div(dbc.Tabs([
        dbc.Tab(label="Modelo Canônico", children=html.Div(KeyValueTable(canonical), className="mt-3")),
        dbc.Tab(label="Entidades e Relações", children=html.Div(OntologyGraphViewer(nodes, edges), className="mt-3")),
        dbc.Tab(label="Validações Semânticas", children=html.Div(KeyValueTable(validation), className="mt-3")),
        dbc.Tab(label="Inferências", children=html.Ul(inference_lis, className="mt-3")),
    ], className="agro-tabs"))


def _inference_list_items(semantic_validation: dict) -> list:
    """Normaliza inferências: nos ciclos reais o campo é contagem (int), não lista."""
    raw = semantic_validation.get("inferences")
    if isinstance(raw, list):
        return [html.Li(str(item)) for item in raw] or [html.Li("Nenhuma inferência registrada")]
    if isinstance(raw, int) and raw > 0:
        return [html.Li(f"{raw} inferência(s) aplicada(s)")]
    rules = semantic_validation.get("rules_applied") or []
    if rules:
        return [html.Li(str(rule)) for rule in rules]
    return [html.Li("Nenhuma inferência registrada")]


def build_provenance_section(ctx: PageContext, context_cycle_id: str | None = None) -> html.Div:
    prov_cycle_id = ctx.cycle_id or ctx.active_cycle.get("cycle_id") or ""
    events = provenance_adapter.list_events_for_context(
        ctx.global_filter, ctx.all_cycles, ctx.active_cycle,
        context_cycle_id=prov_cycle_id, prov_cycle_id=prov_cycle_id or None, cycles_in_context=ctx.cycles,
    )
    enriched = enrich_events(events)
    if not enriched:
        return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
    table_rows = [{
        "evento": e.get("event_type"), "fase": e.get("phase"), "servico": e.get("service"),
        "status": e.get("status", "ok"), "data": e.get("created_at"),
    } for e in enriched]
    graph_list = html.Ul(
        [html.Li(f"{e['from']} → {e['to']}") for e in build_derivation_graph(enriched)],
        className="derivation-timeline mt-3",
    )
    return html.Div(dbc.Tabs([
        dbc.Tab(label="Timeline", children=html.Div(ProvenanceTimeline(enriched), className="mt-3")),
        dbc.Tab(label="Tabela", children=html.Div(DataTable(table_rows, columns=["evento", "fase", "servico", "status", "data"]), className="mt-3")),
        dbc.Tab(label="Payload", children=html.Div(PayloadViewer(enriched[0].get("payload_json"), title="Payload recente"), className="mt-3")),
        dbc.Tab(label="Derivação", children=html.Div(graph_list, className="mt-3")),
    ], className="agro-tabs"))


def build_blockchain_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
    if not is_blockchain_unlocked(cycle):
        lock_msg = blockchain_lock_message(cycle) or EMPTY_BLOCKCHAIN_LOCKED["message"]
        return html.Div(
            dbc.Card(dbc.CardBody([
                html.I(className="fas fa-lock gate-icon d-block"),
                EmptyState(
                    EMPTY_BLOCKCHAIN_LOCKED["title"],
                    lock_msg,
                    icon=EMPTY_BLOCKCHAIN_LOCKED["icon"],
                    action_label="Ir para Aprovação",
                    action_href="/approval",
                ),
            ]), className="agro-card blockchain-gate-card"),
        )
    summary = build_evidence_summary(cycle)
    evidence = cycle.get("evidence_package") or {}
    anchoring = cycle.get("anchoring") or {}
    hashes = summary.get("hashes") or {}
    events = events_for_step(cycle, "blockchain") + events_for_step(cycle, "evidence")
    pkg_rows = blockchain_adapter.build_package_summary_rows(ctx.cycles)
    return html.Div([
        html.Div([ModeBadge(summary.get("mode")), html.Span(f" Pacote: {summary.get('evidence_package_id', '—')}", className="text-muted small ms-2")], className="mb-3"),
        dbc.Tabs([
            dbc.Tab(label="Resumo", children=html.Div([
                DataTable(pkg_rows, columns=["ciclo", "propriedade", "período", "pacote", "status"]) if pkg_rows else EmptyFilterState(),
                BlockchainAnchorCard(evidence, anchoring),
            ], className="mt-3")),
            dbc.Tab(label="Pacote", children=html.Div(EvidencePackageViewer(evidence), className="mt-3")),
            dbc.Tab(label="Hashes", children=html.Div(HashViewer(hashes), className="mt-3")),
            dbc.Tab(label="Merkle Root", children=html.Div(MerkleTreeView(evidence, hashes), className="mt-3")),
            dbc.Tab(label="Eventos", children=html.Ul([html.Li(f"{e.get('event_type')}") for e in events], className="mt-3")),
        ], className="agro-tabs"),
    ])


def build_integrity_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    pkg_options = blockchain_adapter.build_verify_cycle_options(ctx.cycles)
    if not pkg_options:
        return html.Div(EmptyFilterState(no_farm=ctx.no_farm_selected, no_farm_cycles=ctx.no_farm_cycles))
    integrity = cycle.get("integrity") or {}
    summary = build_integrity_summary(cycle)
    message = integrity_message(integrity)
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Select(id="verify-cycle-select", options=pkg_options, value=cycle.get("cycle_id", ""), size="sm"), md=5),
            dbc.Col(dbc.ButtonGroup([
                dbc.Button("Verificar integridade", id="btn-verify-intact", size="sm", className="btn-agro-approve"),
                dbc.Button("Simular divergência", id="btn-verify-tamper", size="sm", className="btn-agro-reject"),
            ]), md=7),
        ], className="mb-3 g-2"),
        html.Div([ModeBadge(integrity.get("mode")), html.Span(f" {message}", className="text-aux ms-2")], className="mb-3"),
        IntegrityComparisonTable({**integrity, "rows": summary.get("rows") or [], "message": message}),
    ])


def build_logs_section(ctx: PageContext) -> html.Div:
    cycle = ctx.active_cycle
    errors = cycle.get("errors") or []
    warnings = cycle.get("warnings") or []
    events = provenance_adapter.list_events_for_context(
        ctx.global_filter, ctx.all_cycles, cycle, cycles_in_context=ctx.cycles,
    )
    err_rows = [{"tipo": "erro", "etapa": e.get("step"), "mensagem": e.get("message")} for e in errors if isinstance(e, dict)]
    warn_rows = [{"tipo": "alerta", "etapa": w.get("step"), "mensagem": w.get("message")} for w in warnings if isinstance(w, dict)]
    ev_rows = [{"tipo": "evento", "etapa": e.get("event_type"), "mensagem": e.get("created_at")} for e in events[:50]]
    rows = err_rows + warn_rows + ev_rows
    table_content = DataTable(rows, columns=["tipo", "etapa", "mensagem"] if rows else [])
    return html.Div(
        dbc.Card(dbc.CardBody([
            html.H6("Erros, alertas e eventos recentes", className="card-title mb-3"),
            html.Div(table_content, className="table-responsive"),
        ]), className="agro-card"),
    )
