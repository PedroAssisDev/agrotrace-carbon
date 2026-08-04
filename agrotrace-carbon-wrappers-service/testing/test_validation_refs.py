"""
Testes unitários por ``ref`` de validação — uma falha aqui indica regressão numa regra específica.

Manter ``COVERED_VALIDATION_REFS`` sincronizado com ``validation_rule_refs()`` (ver teste de completude).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from decimal import Decimal

from wrappers.contracts import ErrorCode, Severity, ValidationIssue, ValidationReport
from wrappers.validators.engine import ValidationEngine, validation_rule_refs
from wrappers.validators import library as V

COVERED_VALIDATION_REFS = frozenset(
    {
        "required_fields",
        "date_valid",
        "non_negative",
        "first_day_of_month",
        "lactating_consistency",
        "dry_consistency",
        "milk_sales_le_production",
        "weight_range_warning",
        "annual_numeric_non_negative",
    }
)


def test_validation_refs_frozen_set_matches_engine() -> None:
    assert validation_rule_refs() == COVERED_VALIDATION_REFS


@pytest.fixture
def engine() -> ValidationEngine:
    return ValidationEngine()


def test_ref_required_fields_fails(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"a": "1"}
    ok = engine.apply(
        [{"ref": "required_fields", "fields": ["a", "b"]}],
        row,
        0,
        report,
    )
    assert ok is False
    assert report.rejected_count >= 1


def test_ref_date_valid_fails(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"d": "not-a-date"}
    ok = engine.apply([{"ref": "date_valid", "field": "d"}], row, 0, report)
    assert ok is False


def test_ref_non_negative_fails(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"x": "-1"}
    ok = engine.apply([{"ref": "non_negative", "field": "x"}], row, 0, report)
    assert ok is False


def test_ref_first_day_of_month_warning(engine: ValidationEngine) -> None:
    from datetime import date

    report = ValidationReport()
    row = {"_parsed_date": date(2021, 1, 15)}
    ok = engine.apply([{"ref": "first_day_of_month", "field": "period_start"}], row, 0, report)
    assert ok is True
    assert report.warnings


def test_ref_lactating_consistency_warning(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"number_of_lactating_cows": "10", "lactating_cows": "5"}
    ok = engine.apply([{"ref": "lactating_consistency"}], row, 0, report)
    assert ok is True
    assert report.warnings


def test_ref_dry_consistency_warning(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"number_of_dry_cows": "3", "dry_cows": "2"}
    ok = engine.apply([{"ref": "dry_consistency"}], row, 0, report)
    assert ok is True
    assert report.warnings


def test_ref_milk_sales_le_production_warning(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"milk_sales": "100", "milk_production": "50"}
    ok = engine.apply([{"ref": "milk_sales_le_production"}], row, 0, report)
    assert ok is True
    assert report.warnings


def test_ref_weight_range_warning(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"w": Decimal("50")}
    ok = engine.apply([{"ref": "weight_range_warning", "field": "w"}], row, 0, report)
    assert ok is True
    assert report.warnings


def test_ref_annual_numeric_non_negative_fails(engine: ValidationEngine) -> None:
    report = ValidationReport()
    row = {"hay": "-0.1"}
    ok = engine.apply(
        [{"ref": "annual_numeric_non_negative", "fields": ["hay"]}],
        row,
        0,
        report,
    )
    assert ok is False


def test_unknown_ref_logs_but_does_not_crash(engine: ValidationEngine, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    report = ValidationReport()
    with caplog.at_level(logging.WARNING):
        ok = engine.apply([{"ref": "totally_unknown_rule_xyz"}], {"a": 1}, 0, report)
    assert ok is True
    assert any("totally_unknown" in r.message for r in caplog.records)
