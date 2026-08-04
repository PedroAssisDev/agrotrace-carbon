import pytest

from emissions.exceptions import TemporalInconsistencyError
from emissions.factor_alignment import align_enteric_factors_to_scope
from emissions.temporal_scope import TemporalScope


def test_align_enteric_yearly_defaults_to_monthly_prorates():
    yearly = {"Lactating_Cows": 120.0}
    monthly = align_enteric_factors_to_scope(
        yearly,
        temporal_scope=TemporalScope.MONTHLY,
        factor_temporal_basis=TemporalScope.YEARLY,
    )
    assert monthly["Lactating_Cows"] == pytest.approx(10.0)


def test_align_enteric_same_scope_no_change():
    factors = {"Lactating_Cows": 100.0}
    out = align_enteric_factors_to_scope(
        factors,
        temporal_scope=TemporalScope.YEARLY,
        factor_temporal_basis=TemporalScope.YEARLY,
    )
    assert out == factors


def test_align_enteric_strict_raises_without_proration():
    yearly = {"Lactating_Cows": 120.0}
    with pytest.raises(TemporalInconsistencyError, match="prorratação"):
        align_enteric_factors_to_scope(
            yearly,
            temporal_scope=TemporalScope.MONTHLY,
            factor_temporal_basis=TemporalScope.YEARLY,
            auto_prorate=False,
        )
