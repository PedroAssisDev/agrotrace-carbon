import pytest

from emissions.emission_intensity import (
    build_milk_intensity_indicators,
    calculate_emission_intensity_per_milk_liter,
)
from emissions.exceptions import CalculationError
from emissions.temporal_scope import TemporalScope


def test_intensity_per_liter():
    res = calculate_emission_intensity_per_milk_liter(
        temporal_scope=TemporalScope.ANNUAL,
        co2e_kg=1000.0,
        milk_liters=10000.0,
    )
    assert res.value == pytest.approx(0.1)
    assert res.unit == "kg CO2e/L"


def test_intensity_rejects_zero_milk():
    with pytest.raises(CalculationError, match="milk_liters"):
        calculate_emission_intensity_per_milk_liter(
            temporal_scope=TemporalScope.ANNUAL,
            co2e_kg=100.0,
            milk_liters=0.0,
        )


def test_build_indicators_skips_missing_milk():
    indicators = build_milk_intensity_indicators(
        temporal_scope=TemporalScope.ANNUAL,
        co2e_kg=500.0,
        milk_liters=None,
    )
    assert indicators == {}
