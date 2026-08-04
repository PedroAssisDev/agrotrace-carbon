"""Canonical hash payloads — single source of truth for write and verify."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from provenance_service.domain.calculation.entities import (
    CalculationParameterSet,
    CalculationParameterValue,
    CalculationResultItem,
    CalculationResultSet,
)
from provenance_service.domain.semantic.entities import CanonicalSnapshot, CanonicalSnapshotItem
from provenance_service.domain.shared.enums import HashAlgorithm
from provenance_service.domain.shared.hashing import compute_hash_hex


def canonical_snapshot_hash_payload(
    *,
    graph_name: str,
    snapshot_label: str,
    schema_version: str | None,
    payload: dict[str, Any] | None,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "graph_name": graph_name,
        "snapshot_label": snapshot_label,
        "schema_version": schema_version,
        "payload": payload,
        "items": items,
    }


def canonical_snapshot_hash_from_entities(
    snapshot: CanonicalSnapshot,
    items: list[CanonicalSnapshotItem],
) -> str:
    item_dicts = [
        {"item_key": i.item_key, **dict(i.payload)}
        for i in sorted(items, key=lambda x: x.item_key)
    ]
    return compute_hash_hex(
        canonical_snapshot_hash_payload(
            graph_name=snapshot.graph_name,
            snapshot_label=snapshot.snapshot_label,
            schema_version=snapshot.schema_version,
            payload=snapshot.payload,
            items=item_dicts,
        )
    )


def calculation_parameter_set_hash_payload(
    *,
    calculation_method_version_id: UUID,
    values: list[dict[str, Any]],
) -> dict[str, Any]:
    # Keys match ProvenanceRecorder.record_calculation_parameter_set
    return {
        "method_version_id": str(calculation_method_version_id),
        "values": values,
    }


def parameter_value_row(value: CalculationParameterValue) -> dict[str, Any]:
    return {
        "name": value.parameter_name,
        "text": value.parameter_value_text,
        "numeric": value.parameter_value_numeric,
        "unit": value.parameter_unit,
        "source": value.parameter_source,
        "is_user_editable": value.is_user_editable,
    }


def calculation_parameter_set_hash_from_entities(
    param_set: CalculationParameterSet,
    values: list[CalculationParameterValue],
) -> str:
    rows = [parameter_value_row(v) for v in sorted(values, key=lambda x: x.parameter_name)]
    return compute_hash_hex(
        calculation_parameter_set_hash_payload(
            calculation_method_version_id=param_set.calculation_method_version_id,
            values=rows,
        )
    )


def calculation_result_set_hash_payload(
    *,
    calculation_execution_id: UUID,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "calculation_execution_id": str(calculation_execution_id),
        "items": items,
    }


def result_item_row(item: CalculationResultItem) -> dict[str, Any]:
    return {
        "type": item.result_type.value,
        "name": item.result_name,
        "value": item.result_value,
        "unit": item.result_unit,
        "dimension_reference": item.dimension_reference,
    }


def calculation_result_set_hash_from_entities(
    result_set: CalculationResultSet,
    items: list[CalculationResultItem],
) -> str:
    rows = [result_item_row(i) for i in sorted(items, key=lambda x: x.result_name)]
    return compute_hash_hex(
        calculation_result_set_hash_payload(
            calculation_execution_id=result_set.calculation_execution_id,
            items=rows,
        )
    )


def compute_subject_hash(payload: dict[str, Any], algorithm: HashAlgorithm) -> str:
    return compute_hash_hex(payload, algorithm=algorithm)
