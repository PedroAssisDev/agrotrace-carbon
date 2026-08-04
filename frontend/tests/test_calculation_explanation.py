"""Testes frontend RF009 — explanation + fatores aplicados (caminho annual)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.calculation_explanation_service import (
    get_explanation_by_calculation_id,
    get_or_build_explanation,
)
from services.calculation_factor_mapping_service import build_factor_rows_for_display
from services.calculation_review_service import ensure_calculation_review, list_review_items
from utils.file_helpers import save_cycle


FRONTEND_ROOT = Path(__file__).resolve().parents[1]


def test_annual_factor_rows_use_applied_not_catalog(agrotrace_data_root: Path) -> None:
    annual_path = FRONTEND_ROOT / "data" / "cycles" / "ANNUAL-2026-FARM-MONTHLY-001.json"
    if not annual_path.exists():
        pytest.skip("fixture annual ausente")
    annual = json.loads(annual_path.read_text(encoding="utf-8"))
    # Catalog has 100; applied factors_used has ~8.33
    catalog_val = (
        ((annual.get("ontology") or {}).get("factor_catalog") or {})
        .get("enteric_ch4_kg_per_animal", {})
        .get("Lactating_Cows")
    )
    applied_val = (
        ((annual.get("calculation") or {}).get("factors_used") or {})
        .get("enteric_ch4_kg_per_animal", {})
        .get("Lactating_Cows")
    )
    assert catalog_val == 100.0
    assert applied_val is not None and float(applied_val) < 20

    annual = ensure_calculation_review(annual)
    enteric_item = next(
        i for i in list_review_items(annual) if i.get("formula_id") == "enteric_fermentation_ch4"
    )
    rows = build_factor_rows_for_display(annual, enteric_item)
    lact = next((r for r in rows if r.get("factor_key") == "Lactating_Cows"), None)
    assert lact is not None
    assert float(lact.get("valor") or 0) < 20
    assert lact.get("source") == "applied_calculation"


def test_get_or_build_explanation_legacy(agrotrace_data_root: Path) -> None:
    annual_path = FRONTEND_ROOT / "data" / "cycles" / "ANNUAL-2026-FARM-MONTHLY-001.json"
    if not annual_path.exists():
        pytest.skip("fixture annual ausente")
    annual = json.loads(annual_path.read_text(encoding="utf-8"))
    # Remove explanation if present to force synthesis
    (annual.get("calculation") or {}).pop("explanation", None)
    expl = get_or_build_explanation(annual)
    assert expl.get("schema_version", "").startswith("calc_explanation")
    assert expl.get("gwp", {}).get("assessment_report")
    source_ids = {s.get("source_id") for s in expl.get("sources") or []}
    assert {"enteric", "manure", "fertilizer", "energy", "total"} <= source_ids


def test_lookup_by_calculation_id(agrotrace_data_root: Path) -> None:
    cycle = {
        "cycle_id": "CYCLE-RF009",
        "calculation_execution_id": "exec-rf009",
        "calculation_result_set_id": "result-rf009",
        "property_id": "FARM-X",
        "reporting_period": "2026-01",
        "calculation": {
            "factors_used": {"gwp": {"CH4": 25.0, "N2O": 298.0}},
            "gwp": {"CH4": 25.0, "N2O": 298.0},
            "inputs": {},
            "flat": {"co2e_total_kg": 1.0, "ch4_enteric_kg": 0, "ch4_manure_kg": 0, "n2o_fertilizer_kg": 0, "co2_energy_kg": 0},
            "method": {"code": "ECOFARM-T1-DAIRY", "version": "1.0.0", "implementation_version": "0.3.1"},
            "preliminary_hash": "abc",
            "explanation": {
                "schema_version": "calc_explanation_v1",
                "calculation_id": "exec-rf009",
                "result_id": "result-rf009",
                "content_hash": "deadbeef",
                "method": {"code": "ECOFARM-T1-DAIRY"},
                "gwp": {"assessment_report": "IPCC AR4", "time_horizon": "100y", "values": []},
                "sources": [],
            },
        },
    }
    save_cycle(cycle)
    found = get_explanation_by_calculation_id("exec-rf009")
    assert found is not None
    assert found.get("content_hash") == "deadbeef"
