"""Smoke tests for the dataclass entities (no SQL involved)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from provenance_service.domain.calculation.entities import (
    CalculationMethod,
    CalculationResultItem,
)
from provenance_service.domain.pipeline.entities import PipelineRun
from provenance_service.domain.prov_core.entities import ProvBundle
from provenance_service.domain.shared.enums import (
    CalculationResultType,
    PipelineRunStatus,
    ProvBundleStatus,
    ProvBundleType,
)


def test_pipeline_run_dataclass_round_trip() -> None:
    run = PipelineRun(
        pipeline_run_id=uuid4(),
        run_code="run-001",
        farm_reference="farm-1",
        reporting_period_reference="2026-Q1",
        run_status=PipelineRunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    assert run.run_status is PipelineRunStatus.RUNNING
    assert run.metadata == {}


def test_prov_bundle_dataclass_defaults() -> None:
    bundle = ProvBundle(
        bundle_id=uuid4(),
        pipeline_run_id=uuid4(),
        bundle_type=ProvBundleType.PIPELINE_RUN,
        status=ProvBundleStatus.OPEN,
        created_at=datetime.now(timezone.utc),
    )
    assert bundle.closed_at is None
    assert bundle.metadata == {}


def test_calculation_result_item_holds_decimal() -> None:
    item = CalculationResultItem(
        calculation_result_item_id=uuid4(),
        calculation_result_set_id=uuid4(),
        result_type=CalculationResultType.EMISSION_TOTAL,
        result_name="co2e",
        result_value=Decimal("1234.567"),
        result_unit="kgCO2e",
    )
    assert item.result_value == Decimal("1234.567")


def test_calculation_method_holds_optional_description() -> None:
    method = CalculationMethod(
        calculation_method_id=uuid4(),
        method_code="ipcc-2019",
        method_name="IPCC 2019 Refinement",
        created_at=datetime.now(timezone.utc),
    )
    assert method.description is None
