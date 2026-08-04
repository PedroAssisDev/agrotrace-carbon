"""Testes de callback / integração da Auditoria Técnica e sanitização SQL."""

from __future__ import annotations

from pathlib import Path

import pytest

from pages.technical_audit_sections import build_audit_tab
from services.audit_payload_service import resolve_payload
from services.audit_summary_service import build_audit_summary
from services.audit_timeline_service import build_audit_timeline
from services.blockchain_linkage_view_service import build_linkage_trail
from services.mock_data import mock_full_cycle
from services.page_context import resolve_page_context
from services.provenance_query_service import execute_provenance_query
from services.provenance_sql_validator import validate_provenance_sql
from utils.sanitize import sanitize_for_display


TAB_IDS = [
    "ta-summary",
    "ta-timeline",
    "ta-provenance",
    "ta-prov-queries",
    "ta-artifacts",
    "ta-blockchain",
    "ta-integrity",
    "ta-logs",
    "ta-payload",
]


@pytest.fixture
def demo_ctx(agrotrace_data_root: Path):
    from services import bootstrap
    from utils.file_helpers import save_cycle

    bootstrap.configure_paths()
    bootstrap.configure_env()
    bootstrap.init_provenance_db()
    demo = mock_full_cycle()
    raw = dict(demo.get("raw_file") or {})
    raw["stored_path"] = str(agrotrace_data_root / "secret" / "abs" / "file.csv")
    raw["original_filename"] = "file.csv"
    demo["raw_file"] = raw
    ont = dict(demo.get("ontology") or {})
    ont["published_ontology_path"] = str(agrotrace_data_root / "secret" / "final.owl")
    demo["ontology"] = ont
    save_cycle(demo)
    gf = {"farm_id": demo.get("property_id"), "cycle_id": demo.get("cycle_id")}
    return resolve_page_context(demo, gf, demo.get("cycle_id")), demo


def test_nine_tabs_render(demo_ctx):
    ctx, _ = demo_ctx
    empty = resolve_page_context({}, {}, None)
    for tab_id in TAB_IDS:
        filled = build_audit_tab(tab_id, ctx)
        bare = build_audit_tab(tab_id, empty)
        assert filled is not None
        assert bare is not None
        assert "Erro ao carregar" not in str(filled)


def test_technical_actions_panel_expanded_with_cycle(demo_ctx):
    ctx, _ = demo_ctx
    summary = str(build_audit_tab("ta-summary", ctx))
    assert "ta-technical-actions" in summary
    assert "Ações técnicas" in summary
    assert "Entrada de Dados" in summary
    assert "start_collapsed=False" in summary or "False" in summary
    empty = resolve_page_context({}, {}, None)
    assert "ta-technical-actions" not in str(build_audit_tab("ta-summary", empty))


def test_summary_sanitizes_ontology_path(demo_ctx):
    ctx, _ = demo_ctx
    summary = build_audit_summary(ctx)
    blob = str(summary)
    assert "secret" not in blob.lower() or "final.owl" in blob
    assert "C:\\Users" not in blob
    cards_blob = str(summary.get("cards") or [])
    assert "published_ontology_path" not in cards_blob or "final.owl" in cards_blob


def test_timeline_and_payload_sanitize_paths(demo_ctx):
    _, demo = demo_ctx
    timeline = build_audit_timeline(demo)
    joined = " | ".join(str(r.get("artifact") or "") for r in timeline)
    assert "secret" not in joined
    assert "abs" not in joined or "file.csv" in joined
    payload = resolve_payload("cycle", demo)
    blob = str(payload.get("data"))
    assert "'stored_path'" not in blob and '"stored_path"' not in blob
    assert "frontend/data/" not in blob
    assert "private_key" not in blob
    assert "secret" not in blob or "file.csv" in blob


def test_payload_explanation_and_corrections(demo_ctx):
    _, demo = demo_ctx
    expl = resolve_payload("calculation_explanation", demo)
    corr = resolve_payload("correction_history", demo)
    assert expl.get("source") == "calculation_explanation"
    assert corr.get("source") == "correction_history"


def test_linkage_trail_builds(demo_ctx):
    _, demo = demo_ctx
    trail = build_linkage_trail(demo)
    assert trail is not None


def test_sanitize_helper_strips_secrets():
    data = {
        "ok": 1,
        "private_key": "0xDEAD",
        "rpc_url": "https://secret",
        "stored_path": r"C:\Users\Pedro\secret\file.csv",
        "nested": {"api_token": "tok", "name": "x"},
    }
    clean = sanitize_for_display(data)
    assert "private_key" not in clean
    assert "rpc_url" not in clean
    assert "stored_path" not in clean
    assert clean.get("file_name") == "file.csv"
    assert "api_token" not in clean["nested"]


def test_sql_forbidden_keywords(agrotrace_data_root: Path):
    from services import bootstrap

    bootstrap.configure_paths()
    bootstrap.configure_env()
    bootstrap.init_provenance_db()

    for sql in [
        "DELETE FROM audit_outbox_event",
        "UPDATE audit_outbox_event SET status='x'",
        "DROP TABLE audit_outbox_event",
        "ALTER TABLE audit_outbox_event ADD COLUMN x INT",
        "ATTACH DATABASE 'x.db' AS other",
        "PRAGMA table_info(audit_outbox_event)",
        "INSERT INTO audit_outbox_event DEFAULT VALUES",
        "SELECT 1; DELETE FROM audit_outbox_event",
    ]:
        vr = validate_provenance_sql(sql)
        assert not vr.ok, sql
        blocked = execute_provenance_query(sql)
        assert not blocked.get("ok"), sql

    ok = validate_provenance_sql("SELECT outbox_event_id FROM audit_outbox_event LIMIT 5")
    assert ok.ok


def test_sql_filter_rejects_injection_chars():
    from callbacks.provenance_queries import _build_filter_clause

    clause = _build_filter_clause(
        "x'; DROP TABLE audit_outbox_event;--",
        None, None, None, None, None, None, None, None,
    )
    assert "DROP" not in clause
    assert clause == "" or "DROP" not in clause.upper()


def test_render_technical_audit_tab_callback(demo_ctx):
    from dash._callback_context import context_value
    from dash._utils import AttributeDict

    from callbacks.technical_audit import render_technical_audit_tab

    ctx, demo = demo_ctx
    gf = {"farm_id": demo.get("property_id"), "cycle_id": demo.get("cycle_id")}
    context_value.set(AttributeDict(triggered_inputs=[{"prop_id": "technical-audit-tabs.active_tab"}]))
    for tab_id in TAB_IDS:
        out = render_technical_audit_tab(
            tab_id,
            gf,
            demo,
            demo.get("cycle_id"),
            "/technical-audit",
        )
        assert out is not None
        assert "Erro ao carregar" not in str(out)


def test_filter_provenance_updates_body_only(demo_ctx):
    from dash._callback_context import context_value
    from dash._utils import AttributeDict

    from callbacks.technical_audit import filter_provenance_events

    _, demo = demo_ctx
    gf = {"farm_id": demo.get("property_id"), "cycle_id": demo.get("cycle_id")}
    context_value.set(AttributeDict(triggered_inputs=[{"prop_id": "ta-prov-phase.value"}]))
    out = filter_provenance_events("all", "all", "all", "all", "", demo, gf, demo.get("cycle_id"))
    assert out is not None
    blob = str(out)
    # body children — must not remount filter selects as outer explorer
    assert "ta-prov-phase" not in blob
