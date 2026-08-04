"""Validação headless dos indicadores do Painel gerencial.

Usa ciclos em estado pendente de aprovação (mock). Para validar o seed real:
    python scripts/reset_and_seed_pending_cycles.py --confirm
    python scripts/validate_pending_approval_seed.py

Uso:
    python scripts/validate_dashboard_indicators.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.indicator_service import (  # noqa: E402
    build_dashboard_chart_series,
    build_dashboard_indicators,
    build_dashboard_tables,
    generate_dashboard_insights,
)
from services.mock_data import mock_pending_cycle  # noqa: E402
from utils.formatting import NA as _NA
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


def _pending_cycle(cid: str, period: str, milk: float, co2e: float, property_id: str, name: str) -> dict:
    cycle = mock_pending_cycle(
        cycle_id=cid,
        property_id=property_id,
        property_name=name,
        reporting_period=period,
    )
    cycle["calculation"] = {
        **(cycle.get("calculation") or {}),
        "co2e_total_kg": co2e,
        "co2e_intensity_per_milk_liter": co2e / milk if milk else 0,
        "by_source": {"Fermentação entérica — CH₄": co2e * 0.6, "Energia — CO₂": co2e * 0.4},
        "by_gas": {"CH4": co2e * 0.7, "CO2": co2e * 0.3},
    }
    cycle["wrapper"] = {
        **(cycle.get("wrapper") or {}),
        "normalized_payload": [
            {
                "milk_production": milk,
                "milk_sales": milk * 0.95,
                "lactating_cows": 20,
                "milk_fat_percentage": 4.1,
                "milk_protein_percentage": 3.3,
                "milk_gross_price": 2.5,
                "employees_during_the_month": 5,
                "pasture_area": 50.0,
                "area_used_for_dairy_activity": 45.0,
                "organic_fertilizer": 1000,
                "non_organic_fertilizer": 500,
                "electricity_grid": 12000,
                "photovoltaic_energy": 3000,
                "total_feed_input": 8000,
                "dry_matter_intake": 18.5,
                "energy_density": 6.2,
                "period_start": f"{period}-01" if len(period) == 7 else period,
            },
        ],
    }
    return cycle


def main() -> int:
    v = Validator()
    cycles = [
        _pending_cycle(
            "C1", "2026-05", 12000, 150000,
            "FARM-MONTHLY-001", "Fazenda Boa Vista Leiteira",
        ),
        _pending_cycle(
            "C2", "2025", 13000, 160000,
            "FARM-ANNUAL-001", "Fazenda Santa Clara Sustentável",
        ),
    ]
    gf = {**DEFAULT_GLOBAL_FILTER, "property_ids": ["FARM-MONTHLY-001", "FARM-ANNUAL-001"]}
    active = cycles[-1]

    ind = build_dashboard_indicators(cycles, active, gf, provenance_events=[], all_cycles=cycles)
    required = (
        "meta", "summary", "productivity", "management", "business",
        "emissions", "sustainability", "data_quality", "pipeline", "auditability",
    )
    v.check("estrutura indicadores", all(k in ind for k in required), str(ind.keys()))
    v.check("summary co2e", (ind["summary"].get("co2e_total_kg") or 0) > 0)
    v.check("pipeline awaiting_approval", (ind["pipeline"].get("awaiting_approval") or 0) >= 1)
    v.check("productivity leite", (ind["productivity"].get("total_milk_liters") or 0) >= 25000)
    v.check("emissions by_source", len(ind["emissions"].get("by_source") or {}) >= 1)

    insights = generate_dashboard_insights(ind)
    v.check("insights não vazio", len(insights) >= 1, str(len(insights)))

    tables = build_dashboard_tables(ind)
    v.check("tabela ranking", len(tables.get("ranking_sources") or []) >= 1)
    v.check("tabela períodos", len(tables.get("period_indicators") or []) == 2)

    charts = build_dashboard_chart_series(ind, cycles)
    v.check("charts productivity", "milk_by_period" in (charts.get("productivity") or {}))
    v.check("charts emissions", "by_source" in (charts.get("emissions") or {}))

    empty = build_dashboard_indicators([], {}, gf, [], [])
    empty_charts = build_dashboard_chart_series(empty, [])
    v.check("ciclos vazios sem exceção", empty.get("meta", {}).get("cycle_count") == 0)
    v.check("charts vazios sem exceção", isinstance(empty_charts, dict))

    print()
    if v.errors:
        print("Dashboard indicators validation: FAIL")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("Dashboard indicators validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
