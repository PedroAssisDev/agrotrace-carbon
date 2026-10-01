import pytest

from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.temporal_scope import (
    TemporalScope,
    normalize_temporal_label,
    require_matching_scope,
)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("monthly", TemporalScope.MONTHLY),
        ("Mensal", TemporalScope.MONTHLY),
        ("annual", TemporalScope.ANNUAL),
        ("ANUAL", TemporalScope.ANNUAL),
    ],
)
def test_normalize_temporal_label_accepts_aliases(label, expected):
    assert normalize_temporal_label(label) is expected


def test_normalize_temporal_label_rejects_yearly_legacy():
    with pytest.raises(CalculationError, match="Escopo temporal inválido"):
        normalize_temporal_label("yearly")


def test_normalize_temporal_label_rejects_invalid():
    with pytest.raises(CalculationError, match="Escopo temporal inválido"):
        normalize_temporal_label("weekly")


def test_require_matching_scope_raises_on_mix():
    with pytest.raises(TemporalInconsistencyError, match="Inconsistência temporal"):
        require_matching_scope(TemporalScope.MONTHLY, TemporalScope.ANNUAL, context="Teste:")
