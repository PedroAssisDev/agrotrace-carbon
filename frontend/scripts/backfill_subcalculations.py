"""Backfill idempotente de subcalculations e input_resolution nos ciclos seed.

Uso:
    cd frontend
    python scripts/backfill_subcalculations.py
    python scripts/backfill_subcalculations.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services import calculation_adapter  # noqa: E402
from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


def _needs_backfill(cycle: dict) -> bool:
    calc = cycle.get("calculation") or {}
    if not calc:
        return False
    subs = calc.get("subcalculations")
    return not subs or len(subs) < 4


def backfill_cycle(cycle: dict, *, dry_run: bool = False) -> bool:
    if not _needs_backfill(cycle):
        return False

    params = dict(cycle.get("calculation_params") or {})
    calc_input = {
        **(cycle.get("ontology") or {}),
        "normalized_data": cycle.get("normalized_data") or [],
        "normalized_payload": cycle.get("normalized_data") or [],
        "reporting_period": cycle.get("reporting_period"),
        "wrapper": cycle.get("wrapper") or {},
    }

    before_co2e = (cycle.get("calculation") or {}).get("co2e_total_kg")
    result = calculation_adapter.run_emission_calculation(calc_input, params)
    subs = result.get("subcalculations") or []
    if not subs:
        print(f"  [SKIP] {cycle.get('cycle_id')}: adapter não retornou subcalculations")
        return False

    cycle["calculation"]["subcalculations"] = subs
    if result.get("input_resolution"):
        cycle["calculation"]["input_resolution"] = result["input_resolution"]
        if cycle["calculation"].get("inputs"):
            cycle["calculation"]["inputs"]["input_resolution"] = result["input_resolution"]
    if result.get("data_source") and cycle["calculation"].get("data_source") == "fallback_defaults":
        cycle["calculation"]["data_source"] = result["data_source"]

    after_co2e = cycle["calculation"].get("co2e_total_kg")
    if before_co2e is not None and after_co2e is not None and abs(before_co2e - after_co2e) > 0.01:
        print(
            f"  [WARN] {cycle.get('cycle_id')}: co2e alterou "
            f"{before_co2e:.2f} → {after_co2e:.2f} (subcalculations adicionados apenas)"
        )

    if not dry_run:
        save_cycle(cycle)
    print(f"  [OK]   {cycle.get('cycle_id')}: {len(subs)} subcalculations")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill subcalculations nos ciclos")
    parser.add_argument("--dry-run", action="store_true", help="Não persiste alterações")
    args = parser.parse_args()

    print("=== backfill_subcalculations ===\n")
    updated = 0
    for cycle in list_cycles():
        if backfill_cycle(cycle, dry_run=args.dry_run):
            updated += 1

    print(f"\n--- {updated} ciclo(s) atualizado(s) ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
