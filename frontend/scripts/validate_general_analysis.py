"""Validação headless da tela Análise Geral.

Uso:
    cd frontend
    python scripts/validate_general_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from pages.sustainability_indicators import layout  # noqa: E402
from services.general_analysis_service import build_overview_kpis, context_message  # noqa: E402
from services.indicator_service import (  # noqa: E402
    build_dashboard_chart_series,
    build_dashboard_indicators,
    build_dashboard_tables,
    build_section_kpis,
    generate_dashboard_insights,
    group_insights_by_severity,
)
from services.mock_data import mock_pending_cycle  # noqa: E402
from utils.formatting import NA as _NA
from utils.global_filter import DEFAULT_GLOBAL_FILTER  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def _cycle(cid: str, period: str, milk: float, co2e: float, property_id: str, cows: float = 20) -> dict:
    c = mock_pending_cycle(cycle_id=cid, property_id=property_id, reporting_period=period)
    c["calculation"] = {
        **(c.get("calculation") or {}),
        "co2e_total_kg": co2e,
        "co2e_intensity_per_milk_liter": co2e / milk if milk else 0,
        "by_source": {"Fermentação entérica — CH₄": co2e * 0.6, "Energia — CO₂": co2e * 0.4},
        "by_gas": {"CH4": co2e * 0.7, "CO2": co2e * 0.3},
        "source": "mock",
    }
    c["wrapper"] = {
        **(c.get("wrapper") or {}),
        "normalized_payload": [{
            "milk_production": milk,
            "lactating_cows": cows,
            "pasture_area": 50.0,
            "period_start": f"{period}-01" if len(period) == 7 else period,
        }],
        "rows_read": 10,
        "rows_valid": 9,
        "source": "mock",
    }
    return c


def main() -> int:
    v = Validator()
    farm = "FARM-ANNUAL-001"
    cycles = [
        _cycle("C-2025-01", "2025-01", 10000, 120000, farm, 18),
        _cycle("C-2025-02", "2025-02", 11000, 130000, farm, 19),
    ]
    gf = {
        **DEFAULT_GLOBAL_FILTER,
        "farm_id": farm,
        "analysis_period_start": "2025-01",
        "analysis_period_end": "2025-02",
        "data_mode": "include_preliminary",
    }
    active = cycles[-1]

    ind = build_dashboard_indicators(cycles, active, gf, [], cycles)
    v.check("meta.integration_mode", ind["meta"].get("integration_mode") in ("mock", "mixed", "real"))
    v.check("pipeline presente", "pipeline" in ind and ind["pipeline"].get("total_cycles") == 2)
    v.check("auditability presente", "auditability" in ind and "provenance_events" in ind["auditability"])
    v.check("emissoes em t CO2e", (ind["emissions"].get("co2e_total_t") or 0) > 0)
    v.check("intensidade consolidada", ind["summary"].get("intensity_consolidated_kg_per_l") not in (None, _NA))
    v.check("producao em L", (ind["productivity"].get("total_milk_liters") or 0) > 0)

    animals = ind["productivity"].get("total_animals")
    v.check("rebanho não supercontado", animals is not None and animals <= 25, f"total_animals={animals}")

    meta = ind["meta"]
    v.check("total_animals_mode", meta.get("total_animals_mode") in ("avg_period", "single", "none"))

    overview = build_overview_kpis(ind)
    v.check("overview KPIs", len(overview) >= 5, str(len(overview)))

    ctx_msg = context_message(meta)
    v.check("mensagem preliminar", ctx_msg is not None and "preliminar" in ctx_msg.lower())

    insights = generate_dashboard_insights(ind)
    groups = group_insights_by_severity(insights)
    v.check("insights agrupados", isinstance(groups, dict))

    tables = build_dashboard_tables(ind)
    v.check("tabela ranking", len(tables.get("ranking_sources") or []) >= 1)
    v.check("tabela ciclos", len(tables.get("cycles_analyzed") or []) == 2)

    charts = build_dashboard_chart_series(ind, cycles)
    v.check("série co2e t", "co2e_by_period_t" in (charts.get("emissions") or {}))

    empty_ind = build_dashboard_indicators([], {}, gf, [], [])
    empty_kpis = build_section_kpis(empty_ind, "emissions")
    v.check("aba vazia sem exceção", isinstance(empty_kpis, list))

    page = layout(active, gf, {"properties": [{"property_id": farm, "name": "Test Farm"}]}, active.get("cycle_id"))
    v.check("layout renderiza", page is not None)

    print()
    if v.errors:
        print("General analysis validation: FAIL")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("General analysis validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
