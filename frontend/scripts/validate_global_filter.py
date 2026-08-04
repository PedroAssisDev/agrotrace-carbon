"""Validação headless do filtro global (fazenda + ciclo).

Uso:
    python scripts/validate_global_filter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.filter_service import get_available_filter_options, get_available_periods  # noqa: E402
from utils.global_filter import (  # noqa: E402
    DEFAULT_GLOBAL_FILTER,
    filter_cycles_by_context,
    filter_events_by_context,
    format_filter_badge,
    format_period_label,
    intensity_trend_from_cycles,
    normalize_filter_state,
    normalize_global_filter,
    period_in_context,
)
from utils.property_filter import filter_by_selected_properties  # noqa: E402


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
    options = get_available_filter_options()
    periods = get_available_periods()

    v.check("catalogo e lista", isinstance(options.get("properties"), list))
    v.check("períodos disponíveis", len(periods) >= 1, str(periods[:5]))

    cycles = [
        {"cycle_id": "C1", "property_id": "FARM-001", "reporting_period": "2026-01", "pipeline_run_id": "R1"},
        {"cycle_id": "C2", "property_id": "FARM-002", "reporting_period": "2026-03", "pipeline_run_id": "R2"},
        {"cycle_id": "C3", "property_id": "FARM-001", "reporting_period": "2026-06", "pipeline_run_id": "R3"},
    ]

    default_filter = normalize_global_filter(DEFAULT_GLOBAL_FILTER)
    v.check("default: sem fazenda", not default_filter.get("farm_id"))
    v.check("default: sem ciclo", not default_filter.get("cycle_id"))
    v.check("filtro vazio retorna 0 ciclos", len(filter_cycles_by_context(cycles, default_filter)) == 0)

    farm_filter = normalize_filter_state({"farm_id": "FARM-001"}, cycles)
    v.check("1 fazenda retorna 1 ciclo ativo", len(filter_cycles_by_context(cycles, farm_filter)) == 1)
    v.check("farm_filter cycle_id definido", farm_filter.get("cycle_id") in {"C1", "C3"}, str(farm_filter.get("cycle_id")))

    cycle_filter = normalize_filter_state({"farm_id": "FARM-001", "cycle_id": "C1"}, cycles)
    v.check("fazenda + ciclo específico", len(filter_cycles_by_context(cycles, cycle_filter)) == 1)
    v.check("cycle_filter period derivado", cycle_filter.get("period") == "2026-01")

    cross_farm = normalize_filter_state({"farm_id": "FARM-001", "cycle_id": "C2"}, cycles)
    v.check("ciclo de outra fazenda não selecionado", cross_farm.get("cycle_id") != "C2", str(cross_farm.get("cycle_id")))

    v.check("period_in_context no ciclo ativo", period_in_context("2026-01", cycle_filter))
    v.check("period_in_context fora", not period_in_context("2026-03", cycle_filter))

    events = [
        {"event_type": "RAW_REGISTERED", "pipeline_run_id": "R1"},
        {"event_type": "CALC_DONE", "pipeline_execution_id": "R2"},
    ]
    ev_filtered = filter_events_by_context(events, cycles, cycle_filter)
    v.check("eventos por ciclo ativo", len(ev_filtered) == 1)

    badge_empty = format_filter_badge(default_filter, options)
    v.check("badge sem fazenda", "Selecione uma fazenda" in badge_empty, badge_empty)
    badge_ctx = format_filter_badge(cycle_filter, options)
    v.check("badge com contexto", badge_ctx.startswith("Filtrando por:"), badge_ctx)
    v.check("format_period_label", format_period_label("2026-01") == "Jan/2026")

    v.check("property_filter compat", len(filter_by_selected_properties(cycles, ["FARM-002"])) == 1)

    trend_cycles = [
        {
            "reporting_period": "2026-01",
            "calculation": {"co2e_total_kg": 800},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
        },
        {
            "reporting_period": "2026-03",
            "calculation": {"co2e_total_kg": 700},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
        },
        {
            "reporting_period": "2026-03",
            "calculation": {"co2e_total_kg": 900},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
        },
    ]
    labels, values = intensity_trend_from_cycles(trend_cycles)
    v.check("intensity_trend labels", labels == ["Jan/2026", "Mar/2026"], str(labels))
    v.check("intensity_trend média", abs(values[1] - 0.8) < 1e-6, str(values))

    v.check("default view_granularity", DEFAULT_GLOBAL_FILTER.get("view_granularity") == "auto")
    v.check("default data_mode", DEFAULT_GLOBAL_FILTER.get("data_mode") == "include_preliminary")

    gf_view = normalize_filter_state({"farm_id": "FARM-001", "view_granularity": "monthly", "data_mode": "all"}, cycles)
    v.check("view_granularity preservado", gf_view.get("view_granularity") == "monthly")
    v.check("data_mode preservado", gf_view.get("data_mode") == "all")

    print()
    if v.errors:
        print("Global filter validation: FAIL")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("Global filter validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
