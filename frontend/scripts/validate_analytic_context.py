"""Validação headless do contexto analítico (PageContext, data_mode, view_granularity).

Uso:
    python scripts/validate_analytic_context.py
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
    seed_temporal_fixtures,
)
from services.page_context import resolve_page_context  # noqa: E402
from utils.global_filter import (  # noqa: E402
    DEFAULT_GLOBAL_FILTER,
    cycles_for_analysis,
    filter_cycles_by_data_mode,
    normalize_filter_state,
)
from utils.temporal_model import (  # noqa: E402
    build_base_series_from_cycles,
    build_temporal_model,
    infer_view_granularity,
    resolve_effective_view_granularity,
    select_temporal_chart_series,
)


def _gf(all_cycles: list[dict], **kwargs) -> dict:
    return normalize_filter_state({"farm_id": kwargs.pop("farm_id"), **kwargs}, all_cycles)


def main() -> int:
    v = CheckCollector()
    print("== Analytic context (fixture isolado) ==\n")

    with isolated_data_root():
        all_cycles = seed_temporal_fixtures(persist=True)
        return _run(v, all_cycles)


def _run(v: CheckCollector, all_cycles: list[dict]) -> int:
    v.check("ciclos carregados", len(all_cycles) >= 3, f"total={len(all_cycles)}")

    # Anual 2021–2025, view=auto → 5 pontos; labels anuais; eixo ≠ intervalo consolidado
    annual_farm = "FARM-ANNUAL-001"
    gf_annual = _gf(all_cycles, farm_id=annual_farm, view_granularity="auto")
    analysis = cycles_for_analysis(all_cycles, gf_annual, None)
    temporal = build_temporal_model(analysis, analysis[0] if analysis else {}, "auto")
    chart = select_temporal_chart_series(temporal)
    v.check("FARM-ANNUAL: view auto != consolidated", temporal.view_granularity != "consolidated", temporal.view_granularity)
    v.check("FARM-ANNUAL: base_series >= 5", len(temporal.base_series) >= 5, str(len(temporal.base_series)))
    if chart:
        labels = [p.get("period_label") for p in chart]
        v.check("FARM-ANNUAL: chart >= 2 pontos", len(chart) >= 2, str(len(chart)))
        v.check(
            "FARM-ANNUAL: eixo sem 'Período consolidado'",
            all(lbl != "Período consolidado" for lbl in labels),
            str(labels[:3]),
        )
        v.check(
            "FARM-ANNUAL: eixo sem intervalo badge",
            not any(" a " in (lbl or "") for lbl in labels),
            str(labels[:3]),
        )

    # Mensal Jan–Jun, view=monthly → 6 pontos
    monthly_farm = "FARM-MONTHLY-001"
    ref = next((c for c in all_cycles if c.get("property_id") == monthly_farm), None)
    gf_jan_jun = _gf(
        all_cycles,
        farm_id=monthly_farm,
        analysis_period_start="2026-01",
        analysis_period_end="2026-06",
        view_granularity="monthly",
    )
    jan_jun = cycles_for_analysis(all_cycles, gf_jan_jun, ref)
    tm_monthly = build_temporal_model(jan_jun, ref, "monthly")
    v.check("Jan-Jun view=monthly: 6 ciclos", len(jan_jun) == 6, str(len(jan_jun)))
    v.check("Jan-Jun view=monthly: 6 buckets", len(tm_monthly.view_series) == 6, str(len(tm_monthly.view_series)))

    # Diário → calc_base monthly (obrigatório — falha se ausente)
    daily_farm = "FARM-DAILY-001"
    daily_analysis = _gf(all_cycles, farm_id=daily_farm)
    daily_cycles = cycles_for_analysis(all_cycles, daily_analysis, None)
    v.check("FARM-DAILY presente", len(daily_cycles) >= 6, str(len(daily_cycles)))
    if daily_cycles:
        tm_daily = build_temporal_model(daily_cycles, daily_cycles[0], "auto")
        v.check(
            "FARM-DAILY: calc_base monthly",
            tm_daily.calculation_base_granularity == "monthly",
            tm_daily.calculation_base_granularity,
        )

    # Intensidade agregada sum(co2e)/sum(milk)
    if jan_jun:
        base = build_base_series_from_cycles(jan_jun, "monthly")
        total_co2e = sum(p.co2e_kg or 0 for p in base)
        total_milk = sum(p.milk_liters or 0 for p in base)
        tm_cons = build_temporal_model(jan_jun, ref, "consolidated")
        if tm_cons.view_series and total_milk:
            got = tm_cons.view_series[0].intensity
            expected = total_co2e / total_milk
            v.check(
                "intensidade consolidada = sum/sum",
                got is not None and abs(got - expected) < 0.01,
                f"got={got} expected={expected}",
            )

    # Aprovação parcial (sintético)
    synthetic = [
        {
            "cycle_id": "S1",
            "property_id": "SYN",
            "reporting_period": "2026-01",
            "calculation": {"co2e_total_kg": 100},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
            "steps": {"calculation": {"status": "DONE"}, "approval": {"status": "APPROVED"}},
            "approval": {"decision": "APPROVED"},
        },
        {
            "cycle_id": "S2",
            "property_id": "SYN",
            "reporting_period": "2026-02",
            "calculation": {"co2e_total_kg": 100},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
            "steps": {"calculation": {"status": "DONE"}, "approval": {"status": "APPROVED"}},
            "approval": {"decision": "APPROVED"},
        },
        {
            "cycle_id": "S3",
            "property_id": "SYN",
            "reporting_period": "2026-03",
            "calculation": {"co2e_total_kg": 100},
            "wrapper": {"normalized_payload": [{"total_milk_production": 1000}]},
            "steps": {"calculation": {"status": "DONE"}, "approval": {"status": "AWAITING_APPROVAL"}},
        },
    ]
    tm_partial = build_temporal_model(synthetic, synthetic[0], "monthly")
    v.check(
        "partial_pending agregado",
        tm_partial.aggregated_approval_status == "partial_pending",
        str(tm_partial.aggregated_approval_status),
    )

    # official_only sem publicados
    if analysis:
        official = filter_cycles_by_data_mode(analysis, "official_only")
        gf_official = _gf(all_cycles, farm_id=annual_farm, data_mode="official_only")
        ctx = resolve_page_context(None, gf_official)
        v.check(
            "official_only: filtered pode ser vazio",
            len(official) == len(ctx.filtered_analysis_cycles),
            f"filter={len(official)} ctx={len(ctx.filtered_analysis_cycles)}",
        )
        if not official:
            v.check("official_only sem dados: no_official_data", ctx.no_official_data is True)

    # normalize_filter_state preserva analysis_period_*
    if ref:
        preserved = normalize_filter_state(
            {
                "farm_id": monthly_farm,
                "analysis_period_start": "2026-02",
                "analysis_period_end": "2026-04",
            },
            all_cycles,
        )
        v.check("preserva analysis_period_start", preserved.get("analysis_period_start") == "2026-02")
        v.check("preserva analysis_period_end", preserved.get("analysis_period_end") == "2026-04")

    # infer auto com 1 ponto ≠ consolidated
    one_point = build_base_series_from_cycles(analysis[:1], "annual") if analysis else []
    if one_point:
        auto_gr = infer_view_granularity("annual", one_point)
        v.check("infer auto 1 ponto != consolidated", auto_gr != "consolidated", auto_gr)
        eff = resolve_effective_view_granularity("monthly", one_point, "auto")
        v.check("resolve auto 1 ponto = calc_base", eff == "monthly", eff)

    # defaults no schema
    v.check("DEFAULT view_granularity", DEFAULT_GLOBAL_FILTER.get("view_granularity") == "auto")
    v.check("DEFAULT data_mode", DEFAULT_GLOBAL_FILTER.get("data_mode") == "include_preliminary")

    return print_structured_summary(v, "Analytic context validation")


if __name__ == "__main__":
    raise SystemExit(main())
