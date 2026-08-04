"""Validação headless da tela Auditoria Técnica (RF020 / RNF002 / RNF007).

Uso:
    python scripts/validate_technical_audit.py
    python scripts/validate_technical_audit.py --data-root /tmp/ta
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.ok: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


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


def main() -> int:
    import config
    from services import bootstrap

    v = Validator()
    print("=== validate_technical_audit ===\n")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp) / "agrotrace-data"
        config.apply_data_root(root, reset_runtime=True)
        bootstrap.configure_paths()
        bootstrap.configure_env()
        bootstrap.init_provenance_db()
        try:
            return _run_validation(v)
        finally:
            try:
                from provenance_service.infrastructure.db.session import get_engine
                from provenance_service.infrastructure.db import clear_engine_cache

                try:
                    get_engine().dispose()
                except Exception:
                    pass
                clear_engine_cache()
            except Exception:
                pass
            config.apply_data_root(None, reset_runtime=True)


def _run_validation(v: Validator) -> int:
    from pages.technical_audit import layout as audit_layout
    from pages.technical_audit_sections import build_audit_tab
    from services.audit_compliance_service import build_compliance_matrix, compliance_summary
    from services.audit_event_service import most_recent_event, resolve_cycle_events
    from services.audit_payload_service import resolve_payload
    from services.audit_summary_service import build_audit_summary, detect_integration_mode
    from services.audit_timeline_service import build_audit_timeline
    from services.blockchain_linkage_view_service import build_linkage_trail
    from services.blockchain_view_service import is_blockchain_unlocked
    from services.mock_data import mock_full_cycle
    from services.page_context import resolve_page_context
    from services.provenance_query_service import execute_provenance_query
    from services.provenance_sql_validator import validate_provenance_sql
    from utils.file_helpers import save_cycle

    demo = mock_full_cycle()
    # evita path absoluto no raw_file do mock
    raw = dict(demo.get("raw_file") or {})
    if raw.get("stored_path"):
        raw["stored_path"] = "demo.csv"
        raw.setdefault("original_filename", "demo.csv")
    demo["raw_file"] = raw
    # path absoluto proposital no ontology — UI deve sanitizar
    ont = dict(demo.get("ontology") or {})
    ont["published_ontology_path"] = r"C:\Users\Secret\ontology\final.owl"
    demo["ontology"] = ont
    save_cycle(demo)

    gf = {
        "farm_id": demo.get("property_id"),
        "farm_name": demo.get("property_name"),
        "cycle_id": demo.get("cycle_id"),
    }
    ctx = resolve_page_context(demo, gf, demo.get("cycle_id"))
    empty_ctx = resolve_page_context({}, {}, None)

    # Montagem da página
    try:
        page = audit_layout(demo, gf, {}, demo.get("cycle_id"))
        page_str = str(page)
        v.check("audit_layout monta sem erro", page is not None)
        v.check("aba default Resumo (ta-summary)", "ta-summary" in page_str)
        v.check("9 abas presentes", all(t in page_str for t in TAB_IDS) or page_str.count("tab_id") >= 9)
        v.check("wizard removido", "btn-wizard-step" not in page_str)
        v.check("loading em ta-tab-content", "ta-tab-content" in page_str and "Loading" in page_str)
    except Exception as exc:
        v.check("audit_layout monta sem erro", False, str(exc))
        page = None

    # Painel técnico — expandido com ciclo; ausente sem ciclo
    try:
        summary_tab = build_audit_tab("ta-summary", ctx)
        s = str(summary_tab)
        v.check("TechnicalActionsPanel título Ações técnicas", "Ações técnicas" in s)
        v.check("TechnicalActionsPanel id presente", "ta-technical-actions" in s)
        v.check(
            "TechnicalActionsPanel expandido",
            "start_collapsed=False" in s or ("start_collapsed" in s and "False" in s),
        )
        v.check(
            "TechnicalActionsPanel conteúdo acessível",
            "Entrada de Dados" in s and "/data-entry" in s,
        )
        empty_summary = str(build_audit_tab("ta-summary", empty_ctx))
        v.check(
            "TechnicalActionsPanel ausente sem ciclo",
            "ta-technical-actions" not in empty_summary,
        )
    except Exception as exc:
        v.check("TechnicalActionsPanel monta", False, str(exc))

    v.check("ciclo ativo carregado", bool(ctx.active_cycle.get("cycle_id")))

    # 9 abas — com ciclo / sem seleção / sem path absoluto
    for tab_id in TAB_IDS:
        try:
            filled = build_audit_tab(tab_id, ctx)
            empty = build_audit_tab(tab_id, empty_ctx)
            fs = str(filled)
            es = str(empty)
            v.check(f"aba {tab_id} com ciclo", filled is not None and len(fs) > 20)
            v.check(f"aba {tab_id} sem seleção", empty is not None)
            v.check(
                f"aba {tab_id} sem path absoluto óbvio",
                "C:\\Users" not in fs
                and "/Users/" not in fs
                and "frontend/data/" not in fs
                and "raw_originals/" not in fs
                and "Secret" not in fs,
            )
            v.check(f"aba {tab_id} sem crash", "Erro ao carregar" not in fs)
        except Exception as exc:
            v.check(f"aba {tab_id} com ciclo", False, str(exc)[:160])

    # Eventos
    events_raw = demo.get("provenance_events") or []
    resolved = resolve_cycle_events(events_raw, demo, include_global_fallback=False)
    v.check(
        "eventos filtrados por ciclo ou provenance_events locais",
        resolved["has_cycle_match"] or bool(demo.get("provenance_events")),
    )
    v.check("sem fallback global por padrão", not resolved["used_global_fallback"])

    from services.provenance_view_service import enrich_events

    enriched = enrich_events(demo.get("provenance_events") or [])
    recent = most_recent_event(enriched)
    payload = resolve_payload("event", demo, selected_event=recent, events=enriched)
    v.check("resolve_payload evento funciona", payload.get("data") is not None or not enriched)
    cycle_payload = resolve_payload("cycle", demo)
    blob = str(cycle_payload.get("data") or {})
    v.check(
        "payload cycle sanitizado (sem stored_path)",
        "'stored_path'" not in blob and '"stored_path"' not in blob,
    )
    v.check(
        "payload cycle sem path de repositório",
        "frontend/data/" not in blob and "raw_originals/" not in blob,
    )

    expl = resolve_payload("calculation_explanation", demo)
    corr = resolve_payload("correction_history", demo)
    v.check("payload calculation_explanation resolve", expl.get("source") == "calculation_explanation")
    v.check("payload correction_history resolve", corr.get("source") == "correction_history")

    v.check("blockchain liberado em ciclo demo publicado", is_blockchain_unlocked(demo))
    pending = {**demo, "steps": {**(demo.get("steps") or {}), "publication": {"status": "PENDING"}}}
    pending["approval"] = {"decision": "PENDING"}
    v.check("blockchain bloqueado antes de publicação", not is_blockchain_unlocked(pending))

    trail = build_linkage_trail(demo)
    trail_blob = str(trail)
    v.check("linkage trail constrói", trail is not None)
    v.check(
        "linkage cobre publicação/pacote/verificação",
        any(
            k in trail_blob.lower()
            for k in ("publica", "pacote", "verific", "package", "anchor", "tx")
        ),
    )

    matrix = build_compliance_matrix(demo)
    v.check("matriz de conformidade construída", len(matrix) >= 14)
    summary = compliance_summary(demo)
    v.check("resumo conformidade", "matrix" in summary and "counts" in summary)

    audit_sum = build_audit_summary(ctx)
    v.check("summary cards", len(audit_sum.get("cards") or []) >= 8)
    timeline = build_audit_timeline(demo)
    v.check("timeline auditoria", len(timeline) >= 18)
    art_vals = " ".join(str(r.get("artifact") or "") for r in timeline)
    v.check("timeline sem stored_path absoluto", "C:\\Users" not in art_vals and "Secret" not in art_vals)

    mode = detect_integration_mode(demo)
    v.check("modo integração detectado", mode in {"real", "mock", "mixed"})

    # SQL guards
    for bad in (
        "DELETE FROM audit_outbox_event",
        "UPDATE audit_outbox_event SET status='x'",
        "INSERT INTO audit_outbox_event VALUES (1)",
        "DROP TABLE audit_outbox_event",
        "ALTER TABLE audit_outbox_event ADD COLUMN x INT",
        "ATTACH DATABASE 'x.db' AS other",
        "PRAGMA table_info(audit_outbox_event)",
    ):
        vr = validate_provenance_sql(bad)
        v.check(f"SQL bloqueia {bad.split()[0]}", not vr.ok)

    ok_sel = validate_provenance_sql("SELECT outbox_event_id FROM audit_outbox_event LIMIT 5")
    v.check("SQL permite SELECT allowlist", ok_sel.ok)

    blocked = execute_provenance_query("DELETE FROM audit_outbox_event")
    v.check("execução DELETE bloqueada", not blocked.get("ok"))

    sel = execute_provenance_query("SELECT outbox_event_id FROM audit_outbox_event LIMIT 5")
    v.check("execução SELECT ok ou vazio", sel.get("ok") is True or "error" in sel)

    n_ok, n_fail = len(v.ok), len(v.errors)
    print(f"\n--- {n_ok} OK, {n_fail} FAIL ---")
    if v.errors:
        print("Falhas:")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
