"""Testes RF009/RNF005 — calc_explanation_v1."""

from __future__ import annotations

import unittest

from emissions.explanation import (
    SCHEMA_VERSION,
    ValueOrigin,
    build_calculation_explanation,
    compute_explanation_hash,
    explanation_from_dict,
)
from emissions.farm_period import FarmPeriodInput
from emissions.temporal_scope import TemporalScope
from orchestration.pipeline import compute_farm_period_emissions


def _sample_inputs(*, days: int = 30) -> dict:
    return {
        "headcounts_by_category": {
            "Lactating_Cows": 20.0,
            "Dry_Cows": 5.0,
            "Heifers": 10.0,
            "Calves": 4.0,
            "Bulls": 1.0,
        },
        "body_weight_kg_by_category": {
            "Lactating_Cows": 550.0,
            "Dry_Cows": 500.0,
            "Heifers": 350.0,
            "Calves": 120.0,
            "Bulls": 700.0,
        },
        "nitrogen_applied_kg": 12.0,
        "energy_consumption_by_vector": {
            "Diesel": 100.0,
            "Gasoline": 10.0,
            "Electricity_Grid": 200.0,
            "Photovoltaic_Energy": 0.0,
        },
        "days_in_period": days,
        "milk_liters": 5000.0,
    }


def _farm(scope: TemporalScope, days: int) -> FarmPeriodInput:
    inp = _sample_inputs(days=days)
    return FarmPeriodInput(
        temporal_scope=scope,
        days_in_period=days,
        headcounts_by_category=inp["headcounts_by_category"],
        body_weight_kg_by_category=inp["body_weight_kg_by_category"],
        nitrogen_applied_kg=inp["nitrogen_applied_kg"],
        energy_consumption_by_vector=inp["energy_consumption_by_vector"],
        milk_liters=inp["milk_liters"],
    )


class CalculationExplanationTests(unittest.TestCase):
    def test_enteric_source(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        self.assertIsNotNone(bundle.explanation)
        enteric = next(s for s in bundle.explanation.sources if s.source_id == "enteric")
        self.assertEqual(enteric.formula_code, "enteric_fermentation_ch4")
        self.assertEqual(enteric.gas, "CH4")
        self.assertTrue(any(f.name and f.name.startswith("enteric_ch4") for f in enteric.factors))
        self.assertIsNotNone(enteric.result_value)

    def test_manure_source(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        manure = next(s for s in bundle.explanation.sources if s.source_id == "manure")
        self.assertEqual(manure.formula_code, "manure_management_ch4")
        self.assertTrue(any("manure_kg_per_kg_bw_per_day" in (f.name or "") for f in manure.factors))

    def test_fertilizer_source(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        fert = next(s for s in bundle.explanation.sources if s.source_id == "fertilizer")
        self.assertEqual(fert.formula_code, "fertilizer_n2o")
        self.assertTrue(any("direct_n2o" in (f.name or "") for f in fert.factors))

    def test_energy_source(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        energy = next(s for s in bundle.explanation.sources if s.source_id == "energy")
        self.assertEqual(energy.formula_code, "energy_co2")
        self.assertTrue(any("energy_co2_kg_per_unit" in (f.name or "") for f in energy.factors))

    def test_total_co2e(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        total = next(s for s in bundle.explanation.sources if s.source_id == "total")
        self.assertEqual(total.formula_code, "total_ghg_co2e")
        self.assertAlmostEqual(total.result_value or 0, bundle.total.co2e_kg, places=6)

    def test_monthly_prorated_enteric_inferred(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30), auto_prorate_factors=True)
        enteric = next(s for s in bundle.explanation.sources if s.source_id == "enteric")
        lact = next(f for f in enteric.factors if f.name and "Lactating_Cows" in f.name)
        self.assertLess(float(lact.value or 0), 20)
        self.assertEqual(lact.origin, ValueOrigin.INFERRED.value)

    def test_annual_enteric_default(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.ANNUAL, 365), auto_prorate_factors=True)
        enteric = next(s for s in bundle.explanation.sources if s.source_id == "enteric")
        lact = next(f for f in enteric.factors if f.name and "Lactating_Cows" in f.name)
        self.assertGreaterEqual(float(lact.value or 0), 50)
        self.assertEqual(bundle.explanation.temporal_granularity, TemporalScope.ANNUAL.value)

    def test_absent_factor_no_fiction(self) -> None:
        expl = build_calculation_explanation(
            flat={"ch4_enteric_kg": 0, "ch4_manure_kg": 0, "n2o_fertilizer_kg": 0, "co2_energy_kg": 0, "co2e_total_kg": 0},
            inputs=_sample_inputs(),
            factors_used={"enteric_ch4_kg_per_animal": {}, "gwp": {"CH4": 25.0, "N2O": 298.0}},
            gwp={"CH4": 25.0, "N2O": 298.0},
            method_code="ECOFARM-T1-DAIRY",
            method_version="1.0.0",
            implementation_version="0.3.1",
            temporal_granularity="monthly",
            absent_factor_keys={"enteric_ch4_kg_per_animal": ["Missing_Category"]},
        )
        enteric = next(s for s in expl.sources if s.source_id == "enteric")
        missing = next(f for f in enteric.factors if f.name and "Missing_Category" in f.name)
        self.assertIsNone(missing.value)
        self.assertEqual(missing.origin, ValueOrigin.ABSENT.value)

    def test_gwp_set(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        gwp = bundle.explanation.gwp
        self.assertIsNotNone(gwp)
        self.assertEqual(gwp.assessment_report, "IPCC AR4")
        self.assertEqual(gwp.time_horizon, "100y")
        names = {v.name for v in gwp.values}
        self.assertIn("CH4", names)
        self.assertIn("N2O", names)

    def test_serialization_roundtrip(self) -> None:
        bundle = compute_farm_period_emissions(_farm(TemporalScope.MONTHLY, 30))
        payload = bundle.explanation.to_dict()
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertTrue(payload["content_hash"])
        restored = explanation_from_dict(payload)
        again = restored.to_dict(include_hash=False)
        self.assertEqual(compute_explanation_hash(again), payload["content_hash"])
        restored2 = explanation_from_dict(payload)
        self.assertEqual(restored2.to_dict()["content_hash"], payload["content_hash"])


if __name__ == "__main__":
    unittest.main()
