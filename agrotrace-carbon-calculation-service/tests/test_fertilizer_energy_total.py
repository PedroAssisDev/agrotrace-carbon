import pytest

from emissions.energy import calculate_energy_co2
from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.fertilizer import calculate_fertilizer_n2o
from emissions.ghg_total import calculate_total_ghg_co2e
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope


def test_fertilizer_yearly_explicit_fraction_parameter():
    """A fração de volatilização deixa de ser hardcoded: deve ser passada explicitamente."""
    res = calculate_fertilizer_n2o(
        temporal_scope=TemporalScope.ANNUAL,
        nitrogen_applied_kg=100.0,
        direct_n2o_emission_factor=0.01,
        indirect_n2o_emission_factor=0.005,
        fraction_n_volatilized=0.1,
    )
    direct = 100 * 0.01
    indirect = 100 * 0.1 * 0.005
    assert res.value == pytest.approx(direct + indirect)
    assert res.unit == "kg N2O"


def test_fertilizer_monthly_nominal():
    res = calculate_fertilizer_n2o(
        temporal_scope=TemporalScope.MONTHLY,
        nitrogen_applied_kg=10.0,
        direct_n2o_emission_factor=0.02,
        indirect_n2o_emission_factor=0.01,
        fraction_n_volatilized=0.0,
    )
    assert res.value == pytest.approx(0.2)
    assert res.temporal_scope is TemporalScope.MONTHLY


def test_fertilizer_rejects_fraction_above_one():
    with pytest.raises(CalculationError, match="fraction_n_volatilized"):
        calculate_fertilizer_n2o(
            temporal_scope=TemporalScope.ANNUAL,
            nitrogen_applied_kg=10.0,
            direct_n2o_emission_factor=0.01,
            indirect_n2o_emission_factor=0.005,
            fraction_n_volatilized=1.5,
        )


def test_fertilizer_rejects_negative_nitrogen():
    with pytest.raises(CalculationError, match="nitrogen_applied_kg"):
        calculate_fertilizer_n2o(
            temporal_scope=TemporalScope.ANNUAL,
            nitrogen_applied_kg=-1.0,
            direct_n2o_emission_factor=0.01,
            indirect_n2o_emission_factor=0.005,
            fraction_n_volatilized=0.0,
        )


def test_energy_explicit_factors_per_vector():
    consumption = {"Diesel": 10.0, "Grid": 100.0}
    factors = {"Diesel": 2.0, "Grid": 0.5}
    res = calculate_energy_co2(
        temporal_scope=TemporalScope.MONTHLY,
        consumption_by_vector=consumption,
        co2_kg_per_unit_consumption=factors,
    )
    assert res.value == pytest.approx(10 * 2.0 + 100 * 0.5)


def test_energy_key_mismatch():
    with pytest.raises(CalculationError, match="Chaves inconsistentes"):
        calculate_energy_co2(
            temporal_scope=TemporalScope.ANNUAL,
            consumption_by_vector={"A": 1.0},
            co2_kg_per_unit_consumption={"B": 1.0},
        )


def _result(value: float, unit: str, scope: TemporalScope) -> CalculationResult:
    return CalculationResult(value=value, unit=unit, temporal_scope=scope)


def test_total_ghg_requires_matching_temporal_scope():
    enteric = _result(1.0, "kg CH4", TemporalScope.ANNUAL)
    manure = _result(1.0, "kg CH4", TemporalScope.MONTHLY)
    fertilizer = _result(1.0, "kg N2O", TemporalScope.ANNUAL)
    energy = _result(1.0, "kg CO2", TemporalScope.ANNUAL)
    with pytest.raises(TemporalInconsistencyError):
        calculate_total_ghg_co2e(
            enteric_ch4=enteric,
            manure_ch4=manure,
            fertilizer_n2o=fertilizer,
            energy_co2=energy,
            gwp_ch4=25.0,
            gwp_n2o=298.0,
        )


def test_total_ghg_gwp_explicit_ipcc_style():
    enteric = _result(2.0, "kg CH4", TemporalScope.ANNUAL)
    manure = _result(0.0, "kg CH4", TemporalScope.ANNUAL)
    fertilizer = _result(1.0, "kg N2O", TemporalScope.ANNUAL)
    energy = _result(10.0, "kg CO2", TemporalScope.ANNUAL)
    total = calculate_total_ghg_co2e(
        enteric_ch4=enteric,
        manure_ch4=manure,
        fertilizer_n2o=fertilizer,
        energy_co2=energy,
        gwp_ch4=25.0,
        gwp_n2o=298.0,
    )
    assert total.temporal_scope is TemporalScope.ANNUAL
    assert total.ch4_co2e_kg == pytest.approx(2.0 * 25.0)
    assert total.n2o_co2e_kg == pytest.approx(1.0 * 298.0)
    assert total.co2_kg == pytest.approx(10.0)
    assert total.co2e_kg == pytest.approx(2.0 * 25.0 + 298.0 + 10.0)


def test_total_ghg_rejects_wrong_unit():
    bad = _result(1.0, "kg CO2", TemporalScope.ANNUAL)
    ok_ch4 = _result(0.0, "kg CH4", TemporalScope.ANNUAL)
    ok_n2o = _result(0.0, "kg N2O", TemporalScope.ANNUAL)
    ok_co2 = _result(0.0, "kg CO2", TemporalScope.ANNUAL)
    with pytest.raises(CalculationError, match="enteric_ch4"):
        calculate_total_ghg_co2e(
            enteric_ch4=bad,
            manure_ch4=ok_ch4,
            fertilizer_n2o=ok_n2o,
            energy_co2=ok_co2,
            gwp_ch4=1.0,
            gwp_n2o=1.0,
        )
