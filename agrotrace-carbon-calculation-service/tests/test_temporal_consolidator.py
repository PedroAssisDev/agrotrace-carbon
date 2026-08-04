import pytest

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult, TotalGhgResult
from emissions.temporal_consolidator import (
    ConsolidationType,
    consolidate_monthly_calculation_results,
    consolidate_monthly_ghg_totals,
)
from emissions.temporal_scope import TemporalScope


def _monthly_ch4(value: float) -> CalculationResult:
    return CalculationResult(
        value=value,
        unit="kg CH4",
        temporal_scope=TemporalScope.MONTHLY,
        description="Enteric fermentation CH4",
    )


def test_consolidate_twelve_monthly_enteric_results():
    monthly = [_monthly_ch4(10.0) for _ in range(12)]
    consolidated = consolidate_monthly_calculation_results(monthly)
    assert consolidated.component.value == pytest.approx(120.0)
    assert consolidated.component.temporal_scope is TemporalScope.YEARLY
    assert consolidated.consolidation_type is ConsolidationType.SUM_OF_MONTHLY
    assert consolidated.source_count == 12


def test_consolidate_rejects_wrong_month_count():
    with pytest.raises(CalculationError, match="12 meses"):
        consolidate_monthly_calculation_results([_monthly_ch4(1.0)])


def test_consolidate_monthly_ghg_totals():
    monthly_totals = [
        TotalGhgResult(
            co2e_kg=100.0,
            temporal_scope=TemporalScope.MONTHLY,
            ch4_co2e_kg=50.0,
            n2o_co2e_kg=40.0,
            co2_kg=10.0,
        )
        for _ in range(12)
    ]
    consolidated = consolidate_monthly_ghg_totals(monthly_totals)
    assert consolidated.total.co2e_kg == pytest.approx(1200.0)
    assert consolidated.total.temporal_scope is TemporalScope.YEARLY
