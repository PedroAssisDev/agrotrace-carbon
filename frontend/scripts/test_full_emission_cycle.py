"""Teste do ciclo completo de emissão — pipeline automática e gate blockchain."""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services import cycle_state, local_orchestrator as orch  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.bootstrap import bootstrap_all  # noqa: E402
from services.provenance_event_catalog import canonical_event_type  # noqa: E402
from utils.file_helpers import save_raw_file  # noqa: E402
import config  # noqa: E402

SAMPLE_CSV = config.SAMPLE_DATA_DIR / "monthly_report.csv"


def _event_types(cycle: dict) -> list[str]:
    return [e.get("event_type") for e in (cycle.get("provenance_events") or [])]


def _has_event(events: list[str], name: str) -> bool:
    canonical = {canonical_event_type(e) for e in events}
    return name in events or canonical_event_type(name) in canonical or name in canonical


def test_auto_after_ingestion() -> list[str]:
    errors: list[str] = []
    raw_meta = save_raw_file(str(SAMPLE_CSV), property_id="FARM-001", reporting_period="2026-01")
    cycle = orch.run_auto_pipeline_after_ingestion(
        raw_meta,
        property_id="FARM-001",
        property_name="Fazenda Teste",
        reporting_period="2026-01",
    )

    if cycle.get("current_status") != "AWAITING_HUMAN_APPROVAL":
        errors.append(f"status esperado AWAITING_HUMAN_APPROVAL, got {cycle.get('current_status')}")
    if is_blockchain_unlocked(cycle):
        errors.append("blockchain desbloqueado após ingestão automática")
    if cycle.get("evidence_package"):
        errors.append("evidence package criado antes da aprovação")
    if not cycle.get("calculation"):
        errors.append("cálculo preliminar ausente")
    return errors


def test_auto_after_approval() -> list[str]:
    errors: list[str] = []
    raw_meta = save_raw_file(str(SAMPLE_CSV), property_id="FARM-002", reporting_period="2026-02")
    cycle = orch.run_auto_pipeline_after_ingestion(
        raw_meta,
        property_id="FARM-002",
        property_name="Fazenda Teste 2",
        reporting_period="2026-02",
    )

    if is_blockchain_unlocked(cycle):
        errors.append("blockchain desbloqueado após cálculo preliminar")

    cycle = orch.run_auto_pipeline_after_approval(cycle, {
        "decision": "APPROVED",
        "approver": "Teste",
        "justification": "OK",
    })

    events = _event_types(cycle)
    if not is_blockchain_unlocked(cycle):
        errors.append("blockchain não desbloqueado após publicação final")
    if not cycle.get("evidence_package", {}).get("merkle_root"):
        errors.append("Merkle Root ausente após evidência")
    if not _has_event(events, "CALCULATION_APPROVED"):
        errors.append("evento ausente: CALCULATION_APPROVED")
    if not _has_event(events, "APPROVED_RESULT_PUBLISHED") and not _has_event(events, "FINAL_ONTOLOGY_PUBLISHED"):
        errors.append("evento ausente: APPROVED_RESULT_PUBLISHED")
    if not cycle.get("publication", {}).get("publication_hash"):
        errors.append("publication_hash ausente no manifesto")
    if not _has_event(events, "EVIDENCE_PACKAGE_CREATED"):
        errors.append("evento ausente: EVIDENCE_PACKAGE_CREATED")
    if not _has_event(events, "PROVENANCE_CHAIN_VERIFIED"):
        errors.append("evento ausente: PROVENANCE_CHAIN_VERIFIED")

    if _has_event(events, "APPROVED_RESULT_PUBLISHED") or _has_event(events, "FINAL_ONTOLOGY_PUBLISHED"):
        idx_pub = next(
            i for i, e in enumerate(events)
            if e in ("APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED")
            or canonical_event_type(e) in ("APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED")
        )
        idx_ev = next(i for i, e in enumerate(events) if "EVIDENCE" in (e or ""))
        if idx_ev < idx_pub:
            errors.append("EVIDENCE_PACKAGE_CREATED antes da publicação")

    return errors


def test_rejection() -> list[str]:
    errors: list[str] = []
    raw_meta = save_raw_file(str(SAMPLE_CSV), property_id="FARM-003", reporting_period="2026-03")
    cycle = orch.run_auto_pipeline_after_ingestion(
        raw_meta,
        property_id="FARM-003",
        property_name="Fazenda Teste 3",
        reporting_period="2026-03",
    )
    cycle = orch.run_auto_pipeline_after_approval(cycle, {
        "decision": "REJECTED",
        "approver": "Teste",
        "justification": "Dados inconsistentes",
    })

    if cycle.get("publication") and cycle.get("publication", {}).get("status") != "NotPublished":
        errors.append("publicação final ocorreu após rejeição")
    if cycle.get("evidence_package"):
        errors.append("pacote de evidência após rejeição")
    if is_blockchain_unlocked(cycle):
        errors.append("blockchain liberado após rejeição")
    if cycle.get("current_status") != "REJECTED":
        errors.append(f"status esperado REJECTED, got {cycle.get('current_status')}")
    return errors


def test_calculation_guard() -> list[str]:
    errors: list[str] = []
    cycle = cycle_state.new_cycle("G", "H", "2026-04")
    cycle["ontology"] = {"entities_created": 1}
    cycle = orch.run_calculation_step(cycle)
    if cycle["steps"]["calculation"]["status"] != "ERROR":
        errors.append("run_calculation_step deveria falhar sem validação semântica")
    return errors


def test_blockchain_guard() -> list[str]:
    errors: list[str] = []
    cycle = cycle_state.new_cycle("I", "J", "2026-05")
    cycle = orch.run_evidence_step(cycle)
    if cycle["steps"]["evidence"]["status"] != "ERROR":
        errors.append("run_evidence_step deveria falhar sem FINAL_ONTOLOGY_PUBLISHED")
    return errors


def main() -> int:
    bootstrap_all()
    all_errors: list[str] = []

    for name, fn in (
        ("auto pós-ingestão", test_auto_after_ingestion),
        ("auto pós-aprovação", test_auto_after_approval),
        ("rejeição", test_rejection),
        ("guard cálculo", test_calculation_guard),
        ("guard blockchain", test_blockchain_guard),
    ):
        errs = fn()
        if errs:
            all_errors.extend(f"[{name}] {e}" for e in errs)
        else:
            print(f"  [OK]   {name}")

    if all_errors:
        print("Full emission cycle test: FAIL")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("Full emission cycle test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
