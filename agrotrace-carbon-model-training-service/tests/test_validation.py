import pandas as pd
import pytest

from model_training_service.data.validation import normalize_approved_results
from model_training_service.domain.errors import DataValidationError


def test_normalization_filters_unapproved_rows_and_aliases_columns():
    raw = pd.DataFrame(
        [
            {
                "Property": "farm-1",
                "Period": "2026-01-15",
                "Granularity": "monthly",
                "Lactating_Cows": 10,
                "Total_Milk_Production": 5000,
                "Total_Emissions": 4.2,
                "approval_status": "approved",
                "publication_status": "published",
            },
            {
                "Property": "farm-2",
                "Period": "2026-01-15",
                "Granularity": "monthly",
                "Lactating_Cows": 12,
                "Total_Milk_Production": 6000,
                "Total_Emissions": 5.0,
                "approval_status": "pending",
                "publication_status": "published",
            },
        ]
    )
    result = normalize_approved_results(raw)
    assert len(result) == 1
    assert result.iloc[0]["property_id"] == "farm-1"
    assert result.iloc[0]["period"] == pd.Timestamp("2026-01-01")


def test_duplicate_periods_are_rejected():
    row = {
        "property_id": "farm-1",
        "period": "2026-01-01",
        "granularity": "monthly",
        "lactating_cows": 10,
        "milk_production_liters": 5000,
        "total_ghg_emissions_tco2e": 4.2,
    }
    with pytest.raises(DataValidationError):
        normalize_approved_results(pd.DataFrame([row, row]))
