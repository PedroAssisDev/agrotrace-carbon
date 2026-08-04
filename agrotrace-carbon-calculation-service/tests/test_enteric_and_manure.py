import pytest

from emissions.defaults import ANIMAL_CATEGORIES
from emissions.enteric_fermentation import calculate_enteric_fermentation_ch4
from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.manure_management import calculate_manure_management_ch4
from emissions.temporal_scope import TemporalScope


def _uniform_heads(n: float = 1.0) -> dict[str, float]:
    return {c: n for c in ANIMAL_CATEGORIES}


def _uniform_weights(w: float = 500.0) -> dict[str, float]:
    return {c: w for c in ANIMAL_CATEGORIES}


def _uniform_manure_day(m: float = 0.08) -> dict[str, float]:
    return {c: m for c in ANIMAL_CATEGORIES}


def _uniform_manure_ef(e: float = 0.001) -> dict[str, float]:
    return {c: e for c in ANIMAL_CATEGORIES}


def test_enteric_yearly_explicit_factors_parametrized():
    ch4_per_animal = {c: 10.0 for c in ANIMAL_CATEGORIES}
    heads = {c: 2.0 for c in ANIMAL_CATEGORIES}
    res = calculate_enteric_fermentation_ch4(
        temporal_scope=TemporalScope.YEARLY,
        headcounts_by_category=heads,
        ch4_kg_per_animal_in_period=ch4_per_animal,
    )
    assert res.temporal_scope is TemporalScope.YEARLY
    assert res.unit == "kg CH4"
    assert res.value == pytest.approx(10.0 * 2.0 * len(ANIMAL_CATEGORIES))


def test_enteric_monthly_same_formula_different_scope_metadata():
    ch4_per_animal = {c: 1.0 for c in ANIMAL_CATEGORIES}
    heads = {c: 1.0 for c in ANIMAL_CATEGORIES}
    res = calculate_enteric_fermentation_ch4(
        temporal_scope=TemporalScope.MONTHLY,
        headcounts_by_category=heads,
        ch4_kg_per_animal_in_period=ch4_per_animal,
    )
    assert res.temporal_scope is TemporalScope.MONTHLY
    assert res.value == pytest.approx(float(len(ANIMAL_CATEGORIES)))


def test_enteric_rejects_key_mismatch():
    heads = {"Lactating_Cows": 1.0}
    factors = {"Dry_Cows": 1.0}
    with pytest.raises(CalculationError, match="Chaves inconsistentes"):
        calculate_enteric_fermentation_ch4(
            temporal_scope=TemporalScope.YEARLY,
            headcounts_by_category=heads,
            ch4_kg_per_animal_in_period=factors,
        )


def test_manure_yearly_multiplies_by_days_explicit():
    res = calculate_manure_management_ch4(
        temporal_scope=TemporalScope.YEARLY,
        headcounts_by_category=_uniform_heads(1.0),
        body_weight_kg_by_category=_uniform_weights(100.0),
        manure_kg_per_kg_body_weight_per_day=_uniform_manure_day(0.1),
        ch4_kg_per_kg_manure=_uniform_manure_ef(0.2),
        days_in_period=365,
    )
    expected = 5 * 1 * 100 * 0.1 * 0.2 * 365
    assert res.value == pytest.approx(expected)
    assert res.temporal_scope is TemporalScope.YEARLY


def test_manure_monthly_uses_thirty_days():
    res = calculate_manure_management_ch4(
        temporal_scope=TemporalScope.MONTHLY,
        headcounts_by_category=_uniform_heads(1.0),
        body_weight_kg_by_category=_uniform_weights(100.0),
        manure_kg_per_kg_body_weight_per_day=_uniform_manure_day(0.1),
        ch4_kg_per_kg_manure=_uniform_manure_ef(0.2),
        days_in_period=30,
    )
    expected = 5 * 1 * 100 * 0.1 * 0.2 * 30
    assert res.value == pytest.approx(expected)


def test_manure_temporal_inconsistency_days_too_large_for_monthly():
    with pytest.raises(TemporalInconsistencyError, match="days_in_period"):
        calculate_manure_management_ch4(
            temporal_scope=TemporalScope.MONTHLY,
            headcounts_by_category=_uniform_heads(1.0),
            body_weight_kg_by_category=_uniform_weights(100.0),
            manure_kg_per_kg_body_weight_per_day=_uniform_manure_day(0.1),
            ch4_kg_per_kg_manure=_uniform_manure_ef(0.2),
            days_in_period=365,
        )


def test_manure_temporal_inconsistency_days_too_small_for_yearly():
    with pytest.raises(TemporalInconsistencyError, match="days_in_period"):
        calculate_manure_management_ch4(
            temporal_scope=TemporalScope.YEARLY,
            headcounts_by_category=_uniform_heads(1.0),
            body_weight_kg_by_category=_uniform_weights(100.0),
            manure_kg_per_kg_body_weight_per_day=_uniform_manure_day(0.1),
            ch4_kg_per_kg_manure=_uniform_manure_ef(0.2),
            days_in_period=30,
        )
