import pytest

from emissions.defaults import ANIMAL_CATEGORIES, ENERGY_VECTORS
from emissions.farm_period import FarmPeriodInput
from emissions.temporal_scope import TemporalScope
from orchestration.pipeline import compute_farm_period_emissions


def _full_farm_input(**overrides: object) -> FarmPeriodInput:
    base = FarmPeriodInput(
        temporal_scope=TemporalScope.YEARLY,
        days_in_period=365,
        headcounts_by_category={c: 10.0 if c == "Lactating_Cows" else 0.0 for c in ANIMAL_CATEGORIES},
        body_weight_kg_by_category={c: 550.0 for c in ANIMAL_CATEGORIES},
        nitrogen_applied_kg=0.0,
        energy_consumption_by_vector={v: 0.0 for v in ENERGY_VECTORS},
        milk_liters=10000.0,
    )
    if not overrides:
        return base
    return FarmPeriodInput(
        temporal_scope=overrides.get("temporal_scope", base.temporal_scope),
        days_in_period=overrides.get("days_in_period", base.days_in_period),
        headcounts_by_category=overrides.get("headcounts_by_category", base.headcounts_by_category),
        body_weight_kg_by_category=overrides.get(
            "body_weight_kg_by_category", base.body_weight_kg_by_category
        ),
        nitrogen_applied_kg=overrides.get("nitrogen_applied_kg", base.nitrogen_applied_kg),
        energy_consumption_by_vector=overrides.get(
            "energy_consumption_by_vector", base.energy_consumption_by_vector
        ),
        milk_liters=overrides.get("milk_liters", base.milk_liters),
        milk_kg_fpcm=overrides.get("milk_kg_fpcm", base.milk_kg_fpcm),
        farm_area_ha=overrides.get("farm_area_ha", base.farm_area_ha),
        period_start=overrides.get("period_start", base.period_start),
        period_end=overrides.get("period_end", base.period_end),
    )


def test_compute_farm_period_emissions_with_milk_intensity():
    farm = _full_farm_input()
    bundle = compute_farm_period_emissions(
        farm,
        enteric_ch4_kg_per_animal={c: 100.0 if c == "Lactating_Cows" else 0.0 for c in ANIMAL_CATEGORIES},
        manure_kg_per_kg_bw_per_day={c: 0.08 for c in ANIMAL_CATEGORIES},
        manure_ch4_kg_per_kg_manure={c: 0.1 for c in ANIMAL_CATEGORIES},
    )
    assert bundle.total.co2e_kg > 0
    assert "co2e_intensity_per_milk_liter" in bundle.indicators
    assert bundle.indicators["co2e_intensity_per_milk_liter"].value == pytest.approx(
        bundle.total.co2e_kg / 10000.0
    )


def test_default_manure_below_enteric_for_lactating_herd():
    """Sanidade: com defaults, CH4 de dejetos deve ficar bem abaixo da entérica."""
    farm = _full_farm_input()  # 10 lactantes, 550 kg
    bundle = compute_farm_period_emissions(farm)

    assert bundle.enteric.value == pytest.approx(1000.0)  # 10 × 100
    # 10 × 550 × 0.08 × 0.001 × 365 ≈ 160.6 kg CH4
    assert bundle.manure.value == pytest.approx(160.6, rel=1e-3)
    assert bundle.manure.value < bundle.enteric.value
    assert bundle.manure.value / bundle.enteric.value < 0.5
    # Por cabeça: ordem IPCC Tier-1 dejetos (~10–50 kg CH4/ano), não milhares
    assert bundle.manure.value / 10.0 < 50.0
    assert bundle.manure.value / 10.0 > 5.0
