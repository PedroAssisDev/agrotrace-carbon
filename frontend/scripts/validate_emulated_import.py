"""Validação do import de uploads emulados.

Uso (após reset):
    python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42
    python scripts/validate_emulated_import.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from scripts._pending_seed_assertions import (  # noqa: E402
    EXPECTED_APPROVAL_COUNT,
    EXPECTED_ENTRY_COUNT,
    SAMPLE_CYCLE_IDS,
    validate_pending_cycle,
    validate_seed_collection,
)
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.cycle_status_service import count_pending_approval, cycles_pending_approval  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def main() -> int:
    v = Validator()
    print("== Validação import emulado — pipeline até pendência ==\n")

    manifest = config.SAVE_FILE_EMULATED_UPLOADS_DIR / "manifest.json"
    v.check("manifest emulated_uploads", manifest.exists(), str(manifest))

    cycles = list_cycles()
    v.check(
        "ciclos persistidos",
        len(cycles) >= EXPECTED_APPROVAL_COUNT,
        f"{len(cycles)} encontrado(s)",
    )

    validate_seed_collection(cycles, v.errors)

    pending = cycles_pending_approval(cycles)
    v.check(
        f"fila pending == {EXPECTED_APPROVAL_COUNT}",
        len(pending) == EXPECTED_APPROVAL_COUNT,
        str(len(pending)),
    )
    v.check(
        "count_pending_approval",
        count_pending_approval(cycles) == EXPECTED_APPROVAL_COUNT,
    )

    by_id = {c.get("cycle_id"): c for c in cycles}
    for cid in SAMPLE_CYCLE_IDS:
        v.check(f"ciclo amostra {cid}", cid in by_id)

    for cycle in cycles:
        if is_blockchain_unlocked(cycle):
            v.errors.append(f"{cycle.get('cycle_id')}: blockchain desbloqueado")
        if cycle.get("evidence_package"):
            v.errors.append(f"{cycle.get('cycle_id')}: evidence_package presente")

    for cid in SAMPLE_CYCLE_IDS:
        cycle = by_id.get(cid)
        if cycle:
            validate_pending_cycle(cycle, v.errors, label=cid)

    v.check(
        "entradas esperadas no manifest",
        manifest.exists()
        and __import__("json").loads(manifest.read_text(encoding="utf-8")).get("entry_count")
        == EXPECTED_ENTRY_COUNT,
        str(EXPECTED_ENTRY_COUNT),
    )

    print()
    if v.errors:
        print(f"Emulated import validation: FAIL ({len(v.errors)} erro(s))")
        for err in v.errors:
            print(f"  - {err}")
        return 1

    print("Emulated import validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
