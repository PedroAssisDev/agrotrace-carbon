import pytest

from emissions.conversion_helpers import sum_monthly_values, uniform_monthly_from_yearly_per_animal
from emissions.defaults import ANIMAL_CATEGORIES, default_enteric_ch4_kg_per_animal_annual
from emissions.temporal_scope import TemporalScope
from environmental_calcs import calculate_enteric_fermentation, calculate_total_emissions


def test_uniform_monthly_from_yearly_is_explicit_proration():
    assert uniform_monthly_from_yearly_per_animal(120.0) == pytest.approx(10.0)


def test_sum_monthly_values_aggregation_path():
    assert sum_monthly_values([1.0, 2.0, 3.0]) == pytest.approx(6.0)


def test_legacy_total_emissions_accepts_explicit_gwp_and_factors():
    """Wrapper legado: fatores e GWP podem ser injetados (parametrizados)."""
    row = {c: 0.0 for c in ANIMAL_CATEGORIES}
    row.update({f"{c}_Weight": 400.0 for c in ANIMAL_CATEGORIES})
    row["Non_Organic_Fertilizer"] = 0.0
    row["Diesel"] = 0.0
    row["Gasoline"] = 0.0
    row["Electricity_Grid"] = 0.0
    row["Photovoltaic_Energy"] = 0.0
    row["Lactating_Cows"] = 1.0
    annual = default_enteric_ch4_kg_per_animal_annual()
    monthly_factors = {k: uniform_monthly_from_yearly_per_animal(v) for k, v in annual.items()}
    y = calculate_enteric_fermentation(row, temporal_scope=TemporalScope.ANNUAL)
    m = calculate_enteric_fermentation(
        row,
        temporal_scope=TemporalScope.MONTHLY,
        ch4_kg_per_animal_in_period=monthly_factors,
    )
    assert m == pytest.approx(y / 12.0, rel=1e-9)
    total = calculate_total_emissions(
        row,
        temporal_scope=TemporalScope.ANNUAL,
        days_in_period=365,
        gwp={"CH4": 25.0, "N2O": 298.0},
    )
    assert total > 0
