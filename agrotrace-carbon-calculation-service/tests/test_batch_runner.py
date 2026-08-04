from pathlib import Path

import pytest

from batch_runner import add_emissions_columns, compute_row_results, run_csv_pipeline
from emissions.defaults import ANIMAL_CATEGORIES, MILK_LITERS_COLUMN
from emissions.temporal_scope import TemporalScope
from orchestration.pipeline import compute_row_emissions


FIXTURES = Path(__file__).parent / "fixtures"


def _minimal_row() -> dict[str, float]:
    row = {c: 1.0 for c in ANIMAL_CATEGORIES}
    row.update({f"{c}_Weight": 500.0 for c in ANIMAL_CATEGORIES})
    row["Non_Organic_Fertilizer"] = 10.0
    row["Diesel"] = 0.0
    row["Gasoline"] = 0.0
    row["Electricity_Grid"] = 0.0
    row["Photovoltaic_Energy"] = 0.0
    row[MILK_LITERS_COLUMN] = 1000.0
    return row


def test_compute_row_results_includes_intensity_when_milk_present():
    result = compute_row_results(_minimal_row(), temporal_scope=TemporalScope.YEARLY)
    assert "co2e_total_kg" in result
    assert "co2e_intensity_per_milk_liter" in result
    assert result["co2e_intensity_per_milk_liter"] == pytest.approx(
        result["co2e_total_kg"] / 1000.0
    )


def test_monthly_scope_prorates_default_enteric_factors():
    row = _minimal_row()
    row["Lactating_Cows"] = 1.0
    for c in ANIMAL_CATEGORIES:
        if c != "Lactating_Cows":
            row[c] = 0.0

    yearly = compute_row_results(row, temporal_scope=TemporalScope.YEARLY, days_in_period=365)
    monthly = compute_row_results(row, temporal_scope=TemporalScope.MONTHLY, days_in_period=30)

    assert monthly["ch4_enteric_kg"] == pytest.approx(yearly["ch4_enteric_kg"] / 12.0, rel=1e-6)


def test_run_csv_pipeline_roundtrip(tmp_path):
    input_path = FIXTURES / "minimal_farm_row.csv"
    output_path = tmp_path / "out.csv"
    df = run_csv_pipeline(str(input_path), str(output_path), temporal_scope=TemporalScope.YEARLY)
    assert "co2e_total_kg" in df.columns
    assert "co2e_intensity_per_milk_liter" in df.columns
    assert output_path.exists()


def test_compute_row_emissions_returns_bundle_with_provenance():
    bundle = compute_row_emissions(_minimal_row(), temporal_scope=TemporalScope.YEARLY)
    assert bundle.provenance is not None
    assert bundle.provenance.method_code == "ECOFARM-T1-DAIRY"


def test_add_emissions_columns_preserves_input_columns():
    import pandas as pd

    row = _minimal_row()
    df = pd.DataFrame([row])
    out = add_emissions_columns(df, temporal_scope=TemporalScope.YEARLY)
    assert MILK_LITERS_COLUMN in out.columns
    assert "co2e_total_kg" in out.columns
