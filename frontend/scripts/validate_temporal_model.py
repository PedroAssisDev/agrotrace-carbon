"""Validação headless do modelo temporal (daily / monthly / annual).

Cria fixtures próprios em AGROTRACE_DATA_ROOT temporário.
Falha se qualquer granularidade prevista estiver ausente.
Jan–Jun = exatamente 6 meses.

Uso:
    python scripts/validate_temporal_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))
_ONTO = REPO_ROOT / "agrotrace-carbon-ontology-manager"
if str(_ONTO) not in sys.path:
    sys.path.insert(0, str(_ONTO))

from scripts._validation_env import (  # noqa: E402
    CheckCollector,
    isolated_data_root,
    print_structured_summary,
    seed_temporal_fixtures,
)
from utils.global_filter import cycles_for_analysis, filter_cycles_by_data_mode, normalize_filter_state  # noqa: E402
from utils.temporal_model import (  # noqa: E402
    aggregate_to_view,
    build_base_series_from_cycles,
    build_temporal_model,
    infer_input_granularity,
    infer_view_granularity,
    resolve_calculation_base_granularity,
    resolve_effective_view_granularity,
    select_temporal_chart_series,
)


def _farm_cycles(all_cycles: list[dict], farm_id: str) -> list[dict]:
    gf = normalize_filter_state({"farm_id": farm_id}, all_cycles)
    return cycles_for_analysis(all_cycles, gf, None)


def main() -> int:
    v = CheckCollector()
    print("== Modelo temporal (fixture isolado: daily/monthly/annual) ==\n")

    with isolated_data_root():
        seeded = seed_temporal_fixtures(persist=True)
        all_cycles = list(seeded)

        v.check("ciclos do fixture", len(all_cycles) == 5 + 12 + 6, f"total={len(all_cycles)}")

        # Granularidades previstas — FALHAR se ausente (não pular)
        required_farms = ("FARM-ANNUAL-001", "FARM-MONTHLY-001", "FARM-DAILY-001")
        present = {c.get("property_id") for c in all_cycles}
        for farm_id in required_farms:
            v.check(f"granularidade prevista presente: {farm_id}", farm_id in present)
        if not all(f in present for f in required_farms):
            print("  [FAIL] granularidades previstas ausentes — abortando restante")
            return print_structured_summary(v, "Modelo temporal")

        scenarios = [
            # farm_id, expected_input, expected_base, min_points, first_label_hint
            ("FARM-ANNUAL-001", "annual", "annual", 5, "2021"),
            ("FARM-MONTHLY-001", "monthly", "monthly", 12, "Jan/2026"),
            ("FARM-DAILY-001", "daily", "monthly", 6, "Jan/2026"),
        ]

        for farm_id, expected_input, expected_base, min_points, first_label_hint in scenarios:
            analysis = _farm_cycles(all_cycles, farm_id)
            v.check(
                f"{farm_id}: ciclos de análise == {min_points}",
                len(analysis) == min_points,
                f"obtido={len(analysis)}",
            )
            if len(analysis) == 0:
                v.check(f"{farm_id}: FAIL — sem ciclos (granularidade ausente)", False)
                continue

            ref = analysis[0]
            input_gr = infer_input_granularity(ref)
            calc_base = resolve_calculation_base_granularity(input_gr)
            v.check(f"{farm_id}: input={expected_input}", input_gr == expected_input, input_gr)
            v.check(f"{farm_id}: calc_base={expected_base}", calc_base == expected_base, calc_base)

            base = build_base_series_from_cycles(analysis, calc_base)
            v.check(f"{farm_id}: base_series >= {min_points}", len(base) >= min_points, str(len(base)))

            temporal = build_temporal_model(
                analysis,
                ref,
                expected_base if expected_base == "annual" else "monthly",
            )
            view = temporal.view_series
            v.check(f"{farm_id}: view_series >= {min_points}", len(view) >= min_points, str(len(view)))

            if view:
                first_label = view[0].period_label
                v.check(
                    f"{farm_id}: primeiro label contém '{first_label_hint}'",
                    first_label_hint in first_label,
                    first_label,
                )

            if farm_id == "FARM-MONTHLY-001":
                # Semestre sobre 12 meses → 2 buckets
                sem = aggregate_to_view(base, "semester", calc_base)
                v.check("Boa Vista semestral: 2 buckets", len(sem) == 2, str(len(sem)))
                if sem:
                    v.check("semestre label", "sem" in sem[0].period_label.lower(), sem[0].period_label)

                # Jan–Jun exatamente 6 meses
                gf_jan_jun = {
                    "farm_id": farm_id,
                    "analysis_period_start": "2026-01",
                    "analysis_period_end": "2026-06",
                }
                filtered = cycles_for_analysis(all_cycles, gf_jan_jun, ref)
                v.check(
                    "cycles_for_analysis Jan-Jun: exatamente 6 ciclos",
                    len(filtered) == 6,
                    f"obtido={len(filtered)} ids={[c.get('cycle_id') for c in filtered]}",
                )
                periods = sorted(c.get("reporting_period") for c in filtered)
                expected_periods = [f"2026-{m:02d}" for m in range(1, 7)]
                v.check(
                    "Jan-Jun periods canônicos",
                    periods == expected_periods,
                    str(periods),
                )

            if farm_id == "FARM-DAILY-001":
                # Daily real: source=daily, calc_base=monthly, 6 pontos Jan-Jun
                v.check("daily: 6 consolidacoes mensais", len(analysis) == 6, str(len(analysis)))
                for c in analysis:
                    entries = c.get("data_entries") or []
                    v.check(
                        f"daily {c.get('reporting_period')}: data_entries > 0",
                        len(entries) >= 28,
                        str(len(entries)),
                    )

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

            # Lot metadata presente
            lots = {c.get("lot_id") for c in analysis if c.get("lot_id")}
            v.check(f"{farm_id}: lot_id presente", bool(lots), str(lots))

        # Fase 2: auto nunca vira consolidated
        annual = _farm_cycles(all_cycles, "FARM-ANNUAL-001")
        v.check("annual disponível para fase 2", len(annual) >= 5, str(len(annual)))
        if annual:
            base_a = build_base_series_from_cycles(annual, "annual")
            auto_gr = resolve_effective_view_granularity("annual", base_a, "auto")
            v.check("auto anual -> annual", auto_gr == "annual", auto_gr)
            tm_auto = build_temporal_model(annual, annual[0], "auto")
            v.check(
                "build_temporal auto != consolidated",
                tm_auto.view_granularity != "consolidated",
                tm_auto.view_granularity,
            )
            chart = select_temporal_chart_series(tm_auto)
            if chart:
                bad = [p.get("period_label") for p in chart if p.get("period_label") == "Período consolidado"]
                v.check("chart auto sem bucket consolidado", not bad, str(bad))

            one = build_base_series_from_cycles(annual[:1], "annual")
            if one:
                v.check(
                    "infer auto 1 ponto != consolidated",
                    infer_view_granularity("annual", one) != "consolidated",
                )

            official = filter_cycles_by_data_mode(annual, "official_only")
            v.check("official_only definido", isinstance(official, list))

        # RF005/RNF006 — cadeia OWL animal → lot → property
        print("\n== Hierarquia organizacional Lot (OWL) ==\n")
        try:
            from ontology import build_full_ontology
            from ontology.cycle_model import (
                OrganizationalConsistencyError,
                upsert_animal,
                upsert_emission_cycle,
                upsert_lot,
                upsert_observation,
                upsert_property,
            )
            from ontology.query_service import resolve_organizational_chain

            onto = build_full_ontology()
            upsert_property(onto, property_id="FARM-DAILY-001", name="Fazenda Daily")
            upsert_lot(onto, lot_id="LOT-D-01", property_id="FARM-DAILY-001")
            upsert_animal(
                onto,
                animal_id="ANIMAL-D-01",
                property_id="FARM-DAILY-001",
                lot_id="LOT-D-01",
            )
            chain = resolve_organizational_chain(onto, animal_id="ANIMAL-D-01")
            v.check(
                "OWL animal->lot->property",
                chain
                == {
                    "animal_id": "ANIMAL-D-01",
                    "lot_id": "LOT-D-01",
                    "property_id": "FARM-DAILY-001",
                },
                str(chain),
            )
            upsert_emission_cycle(
                onto,
                cycle_id="CYCLE-OWL-LOT",
                property_id="FARM-DAILY-001",
                reporting_period="2026-01",
                temporal_granularity="daily",
                organizational_granularity="lot",
                lot_id="LOT-D-01",
            )
            obs = upsert_observation(
                onto,
                cycle_id="CYCLE-OWL-LOT",
                property_id="FARM-DAILY-001",
                variable="herd_count",
                value=12.0,
                lot_id="LOT-D-01",
                organizational_granularity="lot",
            )
            v.check("observação por Lot", obs.get("lot_id") == "LOT-D-01", str(obs.get("lot_id")))
            cross_ok = False
            try:
                upsert_animal(
                    onto,
                    animal_id="ANIMAL-BAD",
                    property_id="FARM-OTHER",
                    lot_id="LOT-D-01",
                )
            except OrganizationalConsistencyError:
                cross_ok = True
            v.check("associação inválida entre properties rejeitada", cross_ok)
        except Exception as exc:
            v.check(f"OWL Lot hierarchy — {type(exc).__name__}: {exc}", False)

    return print_structured_summary(v, "Modelo temporal")


if __name__ == "__main__":
    raise SystemExit(main())
