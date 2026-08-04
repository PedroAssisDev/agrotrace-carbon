"""Validação do import emulado — usa fixture isolado (não assume ambiente operacional).

Uso:
    python scripts/validate_emulated_import.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from scripts._validation_env import (  # noqa: E402
    CheckCollector,
    isolated_data_root,
    print_structured_summary,
    seed_pending_approval_fixtures,
)
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.cycle_status_service import count_pending_approval, cycles_pending_approval  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402


def main() -> int:
    v = CheckCollector()
    print("== Validação import emulado — fixture isolado até pendência ==\n")

    with isolated_data_root():
        seeded = seed_pending_approval_fixtures(persist=True)
        expected = len(seeded)

        cycles = list_cycles()
        v.check(
            "ciclos persistidos no data-root isolado",
            len(cycles) == expected,
            f"esperado={expected} obtido={len(cycles)}",
        )

        pending = cycles_pending_approval(cycles)
        v.check(
            f"fila pending == {expected} (fixture)",
            len(pending) == expected,
            str(len(pending)),
        )
        v.check(
            "count_pending_approval",
            count_pending_approval(cycles) == expected,
        )

        by_prop = {}
        for c in cycles:
            by_prop.setdefault(c.get("property_id"), []).append(c.get("cycle_id"))
        v.check("FARM-MONTHLY-001 presente", "FARM-MONTHLY-001" in by_prop, str(list(by_prop)))
        v.check("FARM-ANNUAL-001 presente", "FARM-ANNUAL-001" in by_prop)
        v.check("FARM-DAILY-001 presente", "FARM-DAILY-001" in by_prop)

        for cycle in cycles:
            if is_blockchain_unlocked(cycle):
                v.check(f"{cycle.get('cycle_id')}: blockchain bloqueado", False)
            if cycle.get("evidence_package"):
                v.check(f"{cycle.get('cycle_id')}: sem evidence_package", False)

        v.check(
            "nenhum ciclo com blockchain desbloqueado",
            all(not is_blockchain_unlocked(c) for c in cycles),
        )
        v.check(
            "nenhum evidence_package prematuro",
            all(not c.get("evidence_package") for c in cycles),
        )
        sample = cycles[0] if cycles else {}
        v.check("sample tem calculation", bool(sample.get("calculation")))
        v.check("sample status awaiting", sample.get("current_status") == "AWAITING_APPROVAL")

    return print_structured_summary(v, "Emulated import validation")


if __name__ == "__main__":
    raise SystemExit(main())
