"""Validação headless do modelo temporal (análise multi-ciclo + agregação).

Uso:
    python scripts/validate_temporal_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from utils.file_helpers import list_cycles  # noqa: E402
from utils.global_filter import cycles_for_analysis, normalize_filter_state  # noqa: E402
from utils.temporal_model import (  # noqa: E402
    aggregate_to_view,
    build_base_series_from_cycles,
    build_temporal_model,
    infer_input_granularity,
    resolve_calculation_base_granularity,
)


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


def _farm_cycles(all_cycles: list[dict], farm_id: str) -> list[dict]:
    gf = normalize_filter_state({"farm_id": farm_id}, all_cycles)
    return cycles_for_analysis(all_cycles, gf, None)


def main() -> int:
    v = Validator()
    all_cycles = list_cycles()

    v.check("ciclos carregados", len(all_cycles) >= 3, f"total={len(all_cycles)}")

    scenarios = [
        ("FARM-ANNUAL-001", "annual", "annual", 5, "2021"),
        ("FARM-MONTHLY-001", "monthly", "monthly", 12, "Jan/2026"),
        ("FARM-DAILY-001", "daily", "monthly", 6, "Jan/2026"),
    ]

    for farm_id, expected_input, expected_base, min_points, first_label_hint in scenarios:
        analysis = _farm_cycles(all_cycles, farm_id)
        v.check(f"{farm_id}: ciclos de análise >= {min_points}", len(analysis) >= min_points, str(len(analysis)))

        if not analysis:
            continue

        ref = analysis[0]
        input_gr = infer_input_granularity(ref)
        calc_base = resolve_calculation_base_granularity(input_gr)
        v.check(f"{farm_id}: input={expected_input}", input_gr == expected_input, input_gr)
        v.check(f"{farm_id}: calc_base={expected_base}", calc_base == expected_base, calc_base)

        base = build_base_series_from_cycles(analysis, calc_base)
        v.check(f"{farm_id}: base_series >= {min_points}", len(base) >= min_points, str(len(base)))

        temporal = build_temporal_model(analysis, ref, expected_base if expected_base == "annual" else "monthly")
        view = temporal.view_series
        v.check(f"{farm_id}: view_series >= {min_points}", len(view) >= min_points, str(len(view)))

        if view:
            first_label = view[0].period_label
            v.check(
                f"{farm_id}: primeiro label contém '{first_label_hint}'",
                first_label_hint in first_label,
                first_label,
            )

        if farm_id == "FARM-MONTHLY-001" and len(base) >= 6:
            sem = aggregate_to_view(base, "semester", calc_base)
            v.check("Boa Vista semestral: 2 buckets Jan-Jun", len(sem) == 2, str(len(sem)))
            if sem:
                v.check("semestre label", "sem" in sem[0].period_label.lower(), sem[0].period_label)

            from utils.global_filter import cycles_for_analysis

            gf_jan_jun = {
                "farm_id": farm_id,
                "analysis_period_start": "2026-01",
                "analysis_period_end": "2026-06",
            }
            filtered = cycles_for_analysis(all_cycles, gf_jan_jun, ref)
            v.check("cycles_for_analysis Jan-Jun: 6 ciclos", len(filtered) == 6, str(len(filtered)))

        if calc_base == "monthly" and len(base) >= 2:
            total_co2e = sum(p.co2e_kg or 0 for p in base)
            total_milk = sum(p.milk_liters or 0 for p in base)
            agg = aggregate_to_view(base, "consolidated", calc_base)
            if agg and total_milk:
                expected_int = total_co2e / total_milk
                got = agg[0].intensity
                v.check(
                    f"{farm_id}: intensidade consolidada = sum/sum",
                    got is not None and abs(got - expected_int) < 0.01,
                    f"got={got} expected={expected_int}",
                )

    # Fase 2: auto nunca vira consolidated; chart series sem label de intervalo
    from utils.temporal_model import (  # noqa: E402
        infer_view_granularity,
        resolve_effective_view_granularity,
        select_temporal_chart_series,
    )

    annual = _farm_cycles(all_cycles, "FARM-ANNUAL-001")
    if annual:
        base_a = build_base_series_from_cycles(annual, "annual")
        auto_gr = resolve_effective_view_granularity("annual", base_a, "auto")
        v.check("auto anual -> annual", auto_gr == "annual", auto_gr)
        tm_auto = build_temporal_model(annual, annual[0], "auto")
        v.check("build_temporal auto != consolidated", tm_auto.view_granularity != "consolidated", tm_auto.view_granularity)
        chart = select_temporal_chart_series(tm_auto)
        if chart:
            bad = [p.get("period_label") for p in chart if p.get("period_label") == "Período consolidado"]
            v.check("chart auto sem bucket consolidado", not bad, str(bad))

    one = build_base_series_from_cycles(annual[:1], "annual") if annual else []
    if one:
        v.check("infer auto 1 ponto != consolidated", infer_view_granularity("annual", one) != "consolidated")

    from utils.global_filter import filter_cycles_by_data_mode  # noqa: E402

    if annual:
        official = filter_cycles_by_data_mode(annual, "official_only")
        v.check("official_only definido", isinstance(official, list))

    print()
    if v.errors:
        print(f"Falhas: {len(v.errors)}")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("Modelo temporal validado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
