"""Valida os ciclos pendentes criados por reset_and_seed_pending_cycles.py.

Uso:
    python scripts/reset_and_seed_pending_cycles.py --confirm
    python scripts/validate_pending_approval_seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from scripts._pending_seed_assertions import (  # noqa: E402
    EXPECTED_APPROVAL_COUNT,
    EXPECTED_ENTRY_COUNT,
    SAMPLE_CYCLE_IDS,
    infer_granularity,
    validate_pending_cycle,
    validate_seed_collection,
)
from services.cycle_status_service import count_pending_approval, cycles_pending_approval  # noqa: E402
from services.dashboard_service import build_dashboard_indicators, generate_dashboard_insights  # noqa: E402
from services.indicator_governance_service import pipeline_counts  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402
from utils.global_filter import DEFAULT_GLOBAL_FILTER  # noqa: E402


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
    print("== Validação do seed — ciclos pendentes de aprovação ==\n")

    cycles = list_cycles()
    v.check(
        "ciclos persistidos",
        len(cycles) >= EXPECTED_APPROVAL_COUNT,
        f"{len(cycles)} encontrado(s)",
    )

    by_id = {c.get("cycle_id"): c for c in cycles}
    for cid in SAMPLE_CYCLE_IDS:
        v.check(f"ciclo {cid}", cid in by_id)

    property_ids = {
        by_id[cid].get("property_id")
        for cid in SAMPLE_CYCLE_IDS
        if cid in by_id
    }
    v.check("duas fazendas distintas (mensal+anual)", len(property_ids) == 2, str(property_ids))

    granularities = {infer_granularity(by_id[cid]) for cid in SAMPLE_CYCLE_IDS if cid in by_id}
    v.check(
        "cenarios mensal/anual cobertos",
        {"monthly", "annual"}.issubset(granularities),
        str(granularities),
    )

    # Diário desativado temporariamente.
    # daily_cycle = by_id.get("MONTHLY-2026-01-FARM-DAILY-001")
    # if daily_cycle:
    #     coverage = daily_cycle.get("temporal_coverage") or {}
    #     v.check(
    #         "diario consolidado mensal",
    #         coverage.get("source_granularity") == "daily"
    #         and coverage.get("granularity") == "monthly",
    #         str(coverage),
    #     )
    #     v.check(
    #         "janeiro com 31 entradas diarias",
    #         len(daily_cycle.get("data_entries") or []) == 31,
    #         str(len(daily_cycle.get("data_entries") or [])),
    #     )

    validate_seed_collection(cycles, v.errors)

    pending = cycles_pending_approval(cycles)
    v.check(
        f"fila de revisão com {EXPECTED_APPROVAL_COUNT} itens",
        len(pending) == EXPECTED_APPROVAL_COUNT,
    )
    v.check(
        f"count_pending_approval == {EXPECTED_APPROVAL_COUNT}",
        count_pending_approval(cycles) == EXPECTED_APPROVAL_COUNT,
    )

    active = cycles[0] if cycles else {}
    indicators = build_dashboard_indicators(cycles, active, DEFAULT_GLOBAL_FILTER, [], cycles)
    pipeline = indicators.get("pipeline") or {}
    v.check(
        "dashboard pipeline awaiting_approval",
        (pipeline.get("awaiting_approval") or 0) >= EXPECTED_APPROVAL_COUNT,
        str(pipeline),
    )
    counts = pipeline_counts(cycles)
    v.check(
        "indicator_service awaiting_approval",
        counts.get("awaiting_approval", 0) >= EXPECTED_APPROVAL_COUNT,
        str(counts),
    )

    insights = generate_dashboard_insights(indicators)
    v.check(
        "insight de aprovação pendente",
        any(i.get("title") in ("Aprovação pendente", "Pendência de aprovação") for i in insights),
        str([i.get("title") for i in insights]),
    )

    for cid in SAMPLE_CYCLE_IDS:
        cycle = by_id.get(cid)
        if cycle:
            validate_pending_cycle(cycle, v.errors, label=cid)

    v.check(
        "total de entradas esperado",
        EXPECTED_ENTRY_COUNT == 17,
        str(EXPECTED_ENTRY_COUNT),
    )

    print()
    if v.errors:
        print(f"Pending approval seed validation: FAIL ({len(v.errors)} erro(s))")
        for err in v.errors:
            print(f"  - {err}")
        return 1

    print("Pending approval seed validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
