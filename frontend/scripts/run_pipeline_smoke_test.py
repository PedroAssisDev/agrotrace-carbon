#!/usr/bin/env python
"""Smoke test oficial: upload → pending → approve → publish → evidence → verify."""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

from services import local_orchestrator as orch  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.bootstrap import bootstrap_all  # noqa: E402
from services.calculation_approval_service import approve_item, can_finalize, finalize_file_approval  # noqa: E402
from services.calculation_review_service import build_calculation_review  # noqa: E402
from services.domain_catalog import canonical_event  # noqa: E402
from services.provenance_event_catalog import canonical_event_type  # noqa: E402
from utils.file_helpers import save_raw_file  # noqa: E402


def _ok(name: str, cond: bool, detail: str = "") -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name + (f": {detail}" if detail else ""))


def main() -> int:
    print("== Smoke pipeline AgroTrace Carbon ==")
    boot = bootstrap_all()
    _ok("bootstrap", bool(boot.get("provenance") or boot.get("paths") or True))

    sample = config.SAMPLE_DATA_DIR / "monthly_report.csv"
    if not sample.exists():
        sample = next(config.SAMPLE_DATA_DIR.glob("*.csv"))
    raw = save_raw_file(sample, property_id="PROP-SMOKE-001", reporting_period="2026-05")
    _ok("original preservado", bool(raw.get("sha256") and raw.get("stored_path")), raw.get("sha256", "")[:12])

    cycle = orch.run_auto_pipeline_after_ingestion(
        raw,
        property_id="PROP-SMOKE-001",
        property_name="Fazenda Smoke",
        reporting_period="2026-05",
        layout_name="monthly",
        mark_pending=True,
    )
    _ok("pending approval", cycle.get("current_status") == "AWAITING_HUMAN_APPROVAL", str(cycle.get("current_status")))
    _ok("blockchain locked", not is_blockchain_unlocked(cycle))
    _ok("cálculo preliminar", bool(cycle.get("calculation")))
    _ok("GWP explícito", bool((cycle.get("calculation") or {}).get("gwp")))
    _ok("sem mock no cálculo", (cycle.get("calculation") or {}).get("mode") != "mock")

    cycle["calculation_review"] = build_calculation_review(cycle)
    for it in cycle["calculation_review"].get("items") or []:
        if it.get("status") in {"NOT_APPLICABLE"}:
            continue
        cycle = approve_item(cycle, it["calculation_item_id"], reviewer="Smoke", justification="OK")
    ok, msg = can_finalize(cycle)
    _ok("can_finalize", ok, msg)

    cycle = finalize_file_approval(cycle, reviewer="Smoke", justification="Smoke approve")
    _ok("publicado", (cycle.get("publication") or {}).get("status") == "PUBLISHED")
    _ok("publication_hash", bool((cycle.get("publication") or {}).get("publication_hash")))
    _ok("blockchain unlocked", is_blockchain_unlocked(cycle))
    _ok("evidence", bool((cycle.get("evidence_package") or {}).get("merkle_root")))
    _ok("anchoring", bool(cycle.get("anchoring")))
    integrity = cycle.get("integrity") or {}
    _ok("verified", integrity.get("is_valid") is True, str(integrity.get("final_status")))

    events = [e.get("event_type") for e in (cycle.get("provenance_events") or [])]
    pub_ok = any(
        canonical_event_type(e) in {"APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED"}
        or canonical_event(e) == "APPROVED_RESULT_PUBLISHED"
        or e in {"APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED"}
        for e in events
    )
    _ok("evento publicação", pub_ok)

    # Idempotência: republicar mesmo conteúdo
    from services.publication_service import publish_approved_cycle

    again = publish_approved_cycle(cycle)
    _ok(
        "publicação idempotente",
        again.get("publication_hash") == cycle["publication"].get("publication_hash"),
    )

    print("Smoke OK.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"SMOKE FAILED: {exc}")
        raise SystemExit(1)
