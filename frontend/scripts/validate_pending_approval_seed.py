"""Valida ciclos pendentes criados por fixture isolado (não assume ambiente operacional).

Uso:
    python scripts/validate_pending_approval_seed.py
    python scripts/validate_pending_approval_seed.py --data-root /tmp/pending
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
from services.cycle_status_service import count_pending_approval, cycles_pending_approval  # noqa: E402
from services.dashboard_service import build_dashboard_indicators, generate_dashboard_insights  # noqa: E402
from services.indicator_governance_service import pipeline_counts  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402
from utils.global_filter import DEFAULT_GLOBAL_FILTER  # noqa: E402


def _infer_granularity(cycle: dict) -> str:
    coverage = cycle.get("temporal_coverage") or {}
    src = str(coverage.get("source_granularity") or "").lower()
    if src in ("annual", "monthly", "daily", "intraday"):
        return src
    return "monthly"


def main() -> int:
    print("== Validação do seed — ciclos pendentes de aprovação (fixture isolado) ==\n")
    v = CheckCollector()

    with isolated_data_root() as root:
        seeded = seed_pending_approval_fixtures(persist=True)
        expected_count = len(seeded)
        expected_property_ids = {c["property_id"] for c in seeded}
        sample_ids = [c["cycle_id"] for c in seeded[:4]]

        cycles = list_cycles()
        fixture_cycles = [c for c in cycles if c.get("seed_fixture")]
        # Quando --data-root é compartilhado com outros validate_*, pode haver ciclos extras.
        # Validamos os registros do fixture, não a contagem global do root.
        v.check(
            "ciclos do fixture persistidos",
            len(fixture_cycles) >= expected_count,
            f"fixture={len(fixture_cycles)} esperado>={expected_count} total_root={len(cycles)}",
        )
        v.check(
            "contagem do fixture (não assume 17 do ambiente global)",
            expected_count == len(seeded) and expected_count >= 3,
            f"fixture_count={expected_count}",
        )

        by_id = {c.get("cycle_id"): c for c in cycles}
        for cid in sample_ids:
            v.check(f"ciclo fixture {cid}", cid in by_id)

        property_ids = {c.get("property_id") for c in fixture_cycles} or {c.get("property_id") for c in cycles}
        v.check(
            "fazendas do fixture presentes",
            expected_property_ids.issubset(property_ids),
            str(sorted(property_ids)),
        )
        v.check(
            "três fazendas (annual/monthly/daily)",
            {"FARM-ANNUAL-001", "FARM-MONTHLY-001", "FARM-DAILY-001"}.issubset(property_ids),
            str(sorted(property_ids)),
        )

        granularities = {_infer_granularity(c) for c in (fixture_cycles or cycles)}
        v.check(
            "cenarios annual/monthly/daily cobertos",
            {"annual", "monthly", "daily"}.issubset(granularities),
            str(granularities),
        )

        annual_n = sum(1 for c in fixture_cycles if c.get("property_id") == "FARM-ANNUAL-001")
        monthly_n = sum(1 for c in fixture_cycles if c.get("property_id") == "FARM-MONTHLY-001")
        daily_n = sum(1 for c in fixture_cycles if c.get("property_id") == "FARM-DAILY-001")
        v.check("annual: 5 ciclos", annual_n == 5, str(annual_n))
        v.check("monthly: 12 ciclos", monthly_n == 12, str(monthly_n))
        v.check("daily consolidado: 6 ciclos (Jan-Jun)", daily_n == 6, str(daily_n))

        pending = cycles_pending_approval(fixture_cycles or cycles)
        v.check(
            f"fila de revisão com >= {expected_count} itens do fixture",
            len(pending) >= expected_count,
            f"pending={len(pending)}",
        )
        v.check(
            f"count_pending_approval fixture >= {expected_count}",
            count_pending_approval(fixture_cycles or cycles) >= expected_count,
        )

        active = (fixture_cycles or cycles)[0] if (fixture_cycles or cycles) else {}
        indicators = build_dashboard_indicators(
            fixture_cycles or cycles, active, DEFAULT_GLOBAL_FILTER, [], fixture_cycles or cycles
        )
        pipeline = indicators.get("pipeline") or {}
        v.check(
            "dashboard pipeline awaiting_approval",
            (pipeline.get("awaiting_approval") or 0) >= expected_count,
            str(pipeline.get("awaiting_approval")),
        )
        counts = pipeline_counts(fixture_cycles or cycles)
        v.check(
            "indicator_service awaiting_approval",
            counts.get("awaiting_approval", 0) >= expected_count,
            str(counts.get("awaiting_approval")),
        )

        insights = generate_dashboard_insights(indicators)
        v.check(
            "insight de aprovação pendente",
            any(i.get("title") in ("Aprovação pendente", "Pendência de aprovação") for i in insights),
            str([i.get("title") for i in insights]),
        )

        # Não deve depender da contagem operacional 17
        v.check(
            "fixture independente do ambiente operacional",
            all(c.get("seed_fixture") for c in seeded),
            "seed_fixture=True em todos",
        )

    return print_structured_summary(v, "Pending approval seed validation")


if __name__ == "__main__":
    raise SystemExit(main())
