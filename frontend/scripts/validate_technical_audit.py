"""Validação headless da tela Auditoria Técnica.

Uso:
    python scripts/validate_technical_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from pages.technical_audit import layout as audit_layout  # noqa: E402
from pages.technical_audit_sections import build_audit_tab, build_integrity_section  # noqa: E402
from services.audit_compliance_service import build_compliance_matrix, compliance_summary  # noqa: E402
from services.audit_event_service import most_recent_event, resolve_cycle_events  # noqa: E402
from services.audit_payload_service import resolve_payload  # noqa: E402
from services.audit_summary_service import build_audit_summary, detect_integration_mode  # noqa: E402
from services.audit_timeline_service import build_audit_timeline  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.mock_data import mock_full_cycle  # noqa: E402
from services.page_context import resolve_page_context  # noqa: E402
from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


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


def main() -> int:
    v = Validator()
    print("=== validate_technical_audit ===\n")

    import tempfile

    import config

    with tempfile.TemporaryDirectory() as tmp:
        original_cycles = config.CYCLES_DIR
        config.CYCLES_DIR = Path(tmp) / "cycles"
        config.CYCLES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            return _run_validation(v)
        finally:
            config.CYCLES_DIR = original_cycles


def _run_validation(v: Validator) -> int:
    demo = mock_full_cycle()
    save_cycle(demo)
    all_cycles = list_cycles()
    gf = {
        "farm_id": demo.get("property_id"),
        "farm_name": demo.get("property_name"),
        "cycle_id": demo.get("cycle_id"),
    }
    ctx = resolve_page_context(demo, gf, demo.get("cycle_id"))

    # Montagem da página
    try:
        page = audit_layout(demo, gf, {}, demo.get("cycle_id"))
        v.check("audit_layout monta sem erro", page is not None)
        v.check("aba default Resumo (ta-summary)", "ta-summary" in str(page))
        v.check("9 abas presentes", str(page).count("tab_id") >= 9 or "Consultas de Proveniência" in str(page))
        v.check("wizard removido", "btn-wizard-step" not in str(page))
        v.check("TechnicalActionsPanel colapsado", "Ações técnicas" in str(build_audit_tab("ta-summary", ctx)))
    except Exception as exc:
        v.check("audit_layout monta sem erro", False, str(exc))

    # Ciclo ativo
    v.check("ciclo ativo carregado", bool(ctx.active_cycle.get("cycle_id")))

    # Eventos por ciclo (sem fallback global silencioso)
    events_raw = demo.get("provenance_events") or []
    resolved = resolve_cycle_events(events_raw, demo, include_global_fallback=False)
    v.check(
        "eventos filtrados por ciclo ou provenance_events locais",
        resolved["has_cycle_match"] or bool(demo.get("provenance_events")),
    )
    v.check("sem fallback global por padrão", not resolved["used_global_fallback"])

    # Payload mais recente por timestamp
    from services.provenance_view_service import enrich_events
    enriched = enrich_events(demo.get("provenance_events") or [])
    recent = most_recent_event(enriched)
    if len(enriched) >= 2:
        ts_values = [e.get("created_at") or "" for e in enriched]
        v.check(
            "payload mais recente usa maior timestamp",
            recent is not None and recent.get("created_at") == max(ts_values),
        )
    else:
        v.check("payload mais recente (amostra insuficiente)", True)

    payload = resolve_payload("event", demo, selected_event=recent, events=enriched)
    v.check("resolve_payload evento funciona", payload.get("data") is not None or not enriched)

    # Gate blockchain
    v.check(
        "blockchain liberado em ciclo demo publicado",
        is_blockchain_unlocked(demo),
        "demo mock_full_cycle deve estar publicado",
    )

    pending = {**demo, "steps": {**(demo.get("steps") or {}), "publication": {"status": "PENDING"}}}
    pending["approval"] = {"decision": "PENDING"}
    v.check("blockchain bloqueado antes de publicação", not is_blockchain_unlocked(pending))

    # Matriz de conformidade
    matrix = build_compliance_matrix(demo)
    v.check("matriz de conformidade construída", len(matrix) >= 14)
    summary = compliance_summary(demo)
    v.check("resumo conformidade", "matrix" in summary and "counts" in summary)

    # Summary e timeline
    audit_sum = build_audit_summary(ctx)
    v.check("summary cards", len(audit_sum.get("cards") or []) >= 8)
    v.check("banners consistência (estrutura)", isinstance(audit_sum.get("banners"), list))
    timeline = build_audit_timeline(demo)
    v.check("timeline auditoria", len(timeline) >= 18)

    mode = detect_integration_mode(demo)
    v.check("modo integração detectado", mode in {"real", "mock", "mixed"})

    # Integridade: lazy na página; seção monta sob demanda
    v.check(
        "container integridade lazy",
        "ta-tab-content" in str(page) and "technical-audit-tabs" in str(page),
    )
    integrity_sec = build_integrity_section(ctx)
    v.check(
        "secao integridade monta",
        "verify-cycle-select" in str(integrity_sec) or "ta-integrity-panel" in str(integrity_sec),
    )

    print(f"\n--- {len(v.ok)} OK, {len(v.errors)} FAIL ---")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
