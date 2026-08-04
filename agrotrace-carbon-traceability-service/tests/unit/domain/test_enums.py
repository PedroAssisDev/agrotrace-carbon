"""Smoke tests for domain enumerations."""

from __future__ import annotations

import pytest

from provenance_service.domain.shared import enums


@pytest.mark.parametrize(
    ("enum_cls", "expected_min_size"),
    [
        (enums.PipelineRunStatus, 5),
        (enums.WrapperExecutionStatus, 4),
        (enums.ProvBundleType, 5),
        (enums.ProvBundleStatus, 3),
        (enums.ProvEntityType, 6),
        (enums.ProvActivityType, 5),
        (enums.ProvAgentType, 3),
        (enums.SemanticExecutionStatus, 4),
        (enums.PublicationStage, 4),
        (enums.CalculationMethodStatus, 3),
        (enums.ParameterSetStatus, 3),
        (enums.CalculationExecutionStatus, 4),
        (enums.CalculationResultSetStatus, 4),
        (enums.CalculationResultType, 6),
        (enums.CalculationReviewDecision, 3),
        (enums.ResultPublicationStatus, 4),
        (enums.HashAlgorithm, 2),
        (enums.HashSubjectKind, 6),
        (enums.BlockchainAnchorStatus, 4),
        (enums.OutboxStatus, 3),
    ],
)
def test_enum_has_expected_size(enum_cls: type, expected_min_size: int) -> None:
    assert len(list(enum_cls)) >= expected_min_size


def test_enums_are_string_valued() -> None:
    assert enums.PipelineRunStatus.RUNNING == "running"
    assert enums.HashAlgorithm.SHA256.value == "sha256"
