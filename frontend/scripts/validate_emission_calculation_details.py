"""Validação headless da tela Cálculos de Emissão (detalhamento técnico).

Uso:
    cd frontend
    python scripts/validate_emission_calculation_details.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

from pages.emission_calculations import layout as calc_layout  # noqa: E402
from services import local_orchestrator as orch  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.emission_detail_service import build_emission_detail_bundle  # noqa: E402
from services.emission_factor_view_service import build_factor_view  # noqa: E402
from services.emission_source_breakdown_service import (  # noqa: E402
    build_gas_breakdown,
    build_source_ranking,
    build_variation_summary,
)
from services.emission_timeseries_service import build_emission_timeseries  # noqa: E402
from services.emission_timeseries_service import build_source_line_series  # noqa: E402
from components.charts import MultiLineTemporalChart  # noqa: E402
from services.mock_data import mock_pending_cycle  # noqa: E402
from services.page_context import resolve_page_context  # noqa: E402
from utils.file_helpers import save_cycle, save_raw_file  # noqa: E402
from utils.global_filter import DEFAULT_GLOBAL_FILTER  # noqa: E402

SAMPLE_CSV = config.SAMPLE_DATA_DIR / "monthly_report.csv"


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


def _mock_cycles() -> tuple[list[dict], dict, dict]:
    farm = "FARM-MONTHLY-001"
    cycles = []
    for i, period in enumerate(["2026-01", "2026-02"], start=1):
        c = mock_pending_cycle(
            cycle_id=f"VAL-CALC-{i}",
            property_id=farm,
            property_name="Fazenda Validação",
            reporting_period=period,
        )
        co2e = 100000 + i * 5000
        c["calculation"] = {
            **(c.get("calculation") or {}),
            "co2e_total_kg": co2e,
            "co2e_intensity_per_milk_liter": co2e / 12000,
            "by_source": {
                "Fermentação entérica — CH₄": co2e * 0.55,
                "Manejo de dejetos — CH₄": co2e * 0.15,
                "Fertilizantes — N₂O": co2e * 0.1,
                "Energia — CO₂": co2e * 0.2,
            },
            "by_gas": {"CH4": co2e * 0.7, "N2O": co2e * 0.1, "CO2": co2e * 0.2},
            "subcalculations": [
                {"id": "enteric", "co2e_kg": co2e * 0.55, "formula": "Tier 1"},
                {"id": "manure", "co2e_kg": co2e * 0.15},
                {"id": "fertilizer", "co2e_kg": co2e * 0.1},
                {"id": "energy", "co2e_kg": co2e * 0.2},
            ],
            "factors_used": {"gwp": {"CH4": 28, "N2O": 265}},
            "inputs": {"headcounts_by_category": {"lactating": 20}},
            "input_resolution": [{"slot": "milk_production", "status": "FOUND"}],
            "data_source": "normalized_data",
            "mode": "real",
            "preliminary_hash": "abc123def456",
        }
        c["wrapper"] = {
            **(c.get("wrapper") or {}),
            "normalized_payload": [{
                "milk_production": 12000,
                "enteric_tco2e": co2e * 0.55 / 1000.0,
                "manure_tco2e": co2e * 0.15 / 1000.0,
                "fertilizer_n2o_co2e": co2e * 0.10,
                "energy_tco2e": co2e * 0.20 / 1000.0,
                "ef_enteric_kg_ch4": 120,
                "period_start": f"{period}-01",
            }],
        }
        c["normalized_data"] = c["wrapper"]["normalized_payload"]
        cycles.append(c)

    gf = {
        **DEFAULT_GLOBAL_FILTER,
        "farm_id": farm,
        "analysis_period_start": "2026-01",
        "analysis_period_end": "2026-02",
        "data_mode": "include_preliminary",
    }
    return cycles, gf, cycles[-1]


def _mock_single_cycle_monthly_history() -> tuple[list[dict], dict, dict]:
    """1 ciclo com histórico mensal em normalized_payload (cenário pipeline/ECOFARM)."""
    farm = "FARM-VAL-MULTI"
    co2e_total = 200000.0
    c = mock_pending_cycle(
        cycle_id="VAL-MONTHLY-HIST",
        property_id=farm,
        property_name="Fazenda Histórico Mensal",
        reporting_period="2026-03",
    )
    c["calculation"] = {
        "co2e_total_kg": co2e_total,
        "co2e_intensity_per_milk_liter": co2e_total / 24000,
        "by_source": {
            "Fermentação entérica — CH₄": co2e_total * 0.55,
            "Manejo de dejetos — CH₄": co2e_total * 0.15,
            "Fertilizantes — N₂O": co2e_total * 0.10,
            "Energia — CO₂": co2e_total * 0.20,
        },
        "by_gas": {"CH4": co2e_total * 0.70, "N2O": co2e_total * 0.10, "CO2": co2e_total * 0.20},
    }
    payload = []
    for i, month in enumerate(["2026-01", "2026-02", "2026-03"], start=1):
        share = i / 6.0
        payload.append({
            "milk_production": 8000 + i * 100,
            "enteric_tco2e": co2e_total * 0.55 * share / 1000.0,
            "manure_tco2e": co2e_total * 0.15 * share / 1000.0,
            "fertilizer_n2o_co2e": co2e_total * 0.10 * share,
            "energy_tco2e": co2e_total * 0.20 * share / 1000.0,
            "period_start": f"{month}-01",
            "period_end": f"{month}-28",
        })
    c["wrapper"] = {"normalized_payload": payload, "layout_id": "monthly:v1"}
    c["normalized_data"] = payload
    gf = {
        **DEFAULT_GLOBAL_FILTER,
        "farm_id": farm,
        "analysis_period_start": "2026-01",
        "analysis_period_end": "2026-03",
        "data_mode": "include_preliminary",
    }
    return [c], gf, c


def main() -> int:
    import tempfile

    v = Validator()
    print("=== validate_emission_calculation_details ===\n")

    cycles, gf, active = _mock_cycles()
    for cyc in cycles:
        save_cycle(cyc)
    ctx = resolve_page_context(active, gf, active.get("cycle_id"))
    work = ctx.filtered_analysis_cycles or ctx.analysis_cycles or cycles

    # Services
    timeseries = build_emission_timeseries(work, ctx.temporal)
    v.check("série temporal total", timeseries.get("has_series"), str(timeseries.get("point_count")))
    v.check("série por fonte", len(timeseries.get("by_source") or {}) >= 2)
    v.check("série por gás", len(timeseries.get("by_gas") or {}) >= 2)
    by_src = timeseries.get("by_source") or {}
    has_source_values = any(
        any(v is not None for v in vals) for vals in by_src.values()
    )
    v.check("série por fonte com valores", has_source_values)
    v.check("total em t CO2e", all(
        x is None or x < 1000 for x in (timeseries.get("total_t") or [])
    ), "valores devem estar em toneladas")

    ranking = build_source_ranking(work, timeseries, all_cycles=cycles, global_filter=gf)
    v.check("ranking fontes", len(ranking.get("rows") or []) >= 2)
    v.check("participação %", all(r.get("participacao_pct") is not None for r in ranking.get("rows") or []))

    gas_bd = build_gas_breakdown(work, timeseries)
    gas_keys = {r.get("gas_key") for r in gas_bd.get("rows") or []}
    v.check("gases CH4/N2O/CO2", {"CH4", "N2O", "CO2"}.issubset(gas_keys))

    variation = build_variation_summary(work, timeseries, all_cycles=cycles, global_filter=gf)
    v.check("variação multi-período", variation.get("has_variation") is True)

    # 1 ciclo + múltiplos meses normalizados → série mensal por fonte
    hist_cycles, hist_gf, hist_active = _mock_single_cycle_monthly_history()
    for cyc in hist_cycles:
        save_cycle(cyc)
    hist_ctx = resolve_page_context(hist_active, hist_gf, hist_active.get("cycle_id"))
    hist_work = hist_ctx.filtered_analysis_cycles or hist_ctx.analysis_cycles or hist_cycles
    hist_ts = build_emission_timeseries(hist_work, hist_ctx.temporal)
    v.check(
        "histórico mensal — labels",
        len(hist_ts.get("labels") or []) >= 2,
        str(len(hist_ts.get("labels") or [])),
    )
    hist_by_src = hist_ts.get("by_source") or {}
    v.check(
        "histórico mensal — fontes",
        len(hist_by_src) >= 2,
        str(list(hist_by_src.keys())[:4]),
    )
    hist_has_vals = any(
        any(v is not None for v in vals) for vals in hist_by_src.values()
    )
    v.check("histórico mensal — valores por fonte", hist_has_vals)
    hist_labels_line, hist_by_src_line = build_source_line_series(hist_work, hist_ctx.temporal)
    hist_chart = MultiLineTemporalChart(
        "test",
        hist_labels_line,
        hist_by_src_line,
        min_points=1,
    )
    v.check("histórico mensal — gráfico linha fonte", hist_chart is not None)
    try:
        hist_page = calc_layout(hist_active, hist_gf, {}, hist_active.get("cycle_id"))
        hist_str = str(hist_page)
        v.check(
            "histórico mensal — sem empty state fonte",
            "Não há dados temporais por fonte emissora" not in hist_str,
        )
    except Exception as exc:
        v.check("histórico mensal — layout", False, str(exc))

    detail = build_emission_detail_bundle(active, work, gf, ranking, gas_bd)
    v.check("detalhe por fonte", len(detail.get("source_details") or []) >= 4)
    v.check("subcálculos/fórmulas", len(detail.get("formulas") or []) >= 1)
    v.check("tier comparison quando Tier2", detail.get("tier_comparison") is not None)

    factor_view = build_factor_view(active)
    v.check("fatores presentes", factor_view.get("has_factors") or not factor_view.get("legacy_schema"))

    # Pipeline real (sem blockchain) — isolado em temp dir
    if SAMPLE_CSV.exists():
        with tempfile.TemporaryDirectory() as tmp:
            original_cycles = config.CYCLES_DIR
            original_originals = config.SAVE_FILE_ORIGINALS_DIR
            config.CYCLES_DIR = Path(tmp) / "cycles"
            config.CYCLES_DIR.mkdir(parents=True, exist_ok=True)
            config.SAVE_FILE_ORIGINALS_DIR = Path(tmp) / "originals"
            config.SAVE_FILE_ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
            try:
                raw_meta = save_raw_file(
                    str(SAMPLE_CSV),
                    property_id="FARM-VAL-CALC",
                    reporting_period="2026-03",
                )
                pipeline_cycle = orch.run_auto_pipeline_after_ingestion(
                    raw_meta,
                    property_id="FARM-VAL-CALC",
                    property_name="Fazenda Pipeline Val",
                    reporting_period="2026-03",
                )
                v.check("pipeline gera cálculo", bool(pipeline_cycle.get("calculation")))
                v.check("blockchain bloqueado pós-ingestão", not is_blockchain_unlocked(pipeline_cycle))
                v.check("sem evidence package", not pipeline_cycle.get("evidence_package"))
            finally:
                config.CYCLES_DIR = original_cycles
                config.SAVE_FILE_ORIGINALS_DIR = original_originals
    else:
        v.check("sample CSV disponível", False, str(SAMPLE_CSV))

    # Layout da página
    try:
        page = calc_layout(active, gf, {}, active.get("cycle_id"))
        page_str = str(page)
        v.check("layout monta sem erro", page is not None)
        v.check("seção temporal", "Evolução temporal" in page_str)
        v.check("ranking fontes na UI", "Ranking de fontes" in page_str or "Emissões por fonte" in page_str)
        line_labels, line_by_src = build_source_line_series(work, ctx.temporal)
        line_chart = MultiLineTemporalChart("test", line_labels, line_by_src, min_points=1)
        v.check("gráfico linha por fonte", line_chart is not None)
        v.check("próxima ação", "Próxima ação" in page_str)
        v.check("preliminar sinalizado", "preliminar" in page_str.lower() or "Preliminar" in page_str)
        v.check("sem blockchain na tela", "ancoragem" not in page_str.lower() and "merkle" not in page_str.lower())
    except Exception as exc:
        v.check("layout monta sem erro", False, str(exc))

    # Tier 2 ausente
    no_tier = mock_pending_cycle(cycle_id="VAL-NO-TIER", property_id="FARM-X", reporting_period="2026-04")
    no_tier["calculation"] = active["calculation"]
    no_tier["wrapper"] = {"normalized_payload": [{"milk_production": 1000}]}
    detail_no = build_emission_detail_bundle(no_tier, [no_tier], gf, ranking, gas_bd)
    v.check("sem Tier2 quando ausente", detail_no.get("tier_comparison") is None)

    print(f"\n=== Resultado: {len(v.errors)} falha(s) ===")
    for e in v.errors:
        print(f"  - {e}")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
