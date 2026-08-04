"""Regenera EmissionResult / EmissionCycle a partir de ciclos JSON existentes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "agrotrace-carbon-ontology-manager"))
sys.path.insert(0, str(REPO / "agrotrace-carbon-calculation-service"))

from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


def migrate_one(cycle: dict, *, recalc: bool) -> dict:
    from services.ontology_result_service import (
        persist_activity_observations,
        persist_calculation_results,
    )

    report = {"cycle_id": cycle.get("cycle_id"), "ok": False, "errors": []}
    if not cycle.get("property_id"):
        report["errors"].append("property_id ausente")
        return report
    if not (cycle.get("normalized_data") or (cycle.get("wrapper") or {}).get("normalized_payload")):
        report["errors"].append("normalized_data ausente")
        return report

    try:
        persist_activity_observations(cycle)
    except Exception as exc:
        report["errors"].append(f"observações: {exc}")
        return report

    calc = cycle.get("calculation")
    if recalc or not calc:
        try:
            from services import local_orchestrator

            cycle = local_orchestrator.run_calculation_step(cycle)
            calc = cycle.get("calculation")
        except Exception as exc:
            report["errors"].append(f"recalc: {exc}")
            return report
    elif calc:
        try:
            persist_calculation_results(cycle, calc, status="preliminary")
        except Exception as exc:
            report["errors"].append(f"persist results: {exc}")
            return report

    save_cycle(cycle)
    report["ok"] = True
    report["results"] = (cycle.get("ontology_results") or {}).get("count")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra ciclos JSON → EmissionResult OWL")
    parser.add_argument("--recalc", action="store_true", help="Recalcula via pipeline")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cycle-id", type=str, default=None)
    args = parser.parse_args()

    cycles = list_cycles()
    if args.cycle_id:
        cycles = [c for c in cycles if c.get("cycle_id") == args.cycle_id]
    if args.limit:
        cycles = cycles[: args.limit]

    reports = []
    for c in cycles:
        # list_cycles pode retornar summaries — carregar completo
        from utils.file_helpers import get_cycle

        full = get_cycle(c["cycle_id"]) or c
        reports.append(migrate_one(full, recalc=args.recalc))

    ok = sum(1 for r in reports if r["ok"])
    fail = len(reports) - ok
    out = {"migrated": ok, "failed": fail, "reports": reports}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    path = ROOT / "data" / "migration_ontology_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
