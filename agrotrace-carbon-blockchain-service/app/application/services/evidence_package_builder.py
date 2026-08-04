from __future__ import annotations

import json
from uuid import UUID

from app.domain.entities import EvidenceItem, EvidencePackage
from app.domain.ports.provenance_ports import ProvenanceDataReaderPort, ProvenanceEvent
from app.domain.services.canonical_json_service import to_canonical_json
from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root
from app.domain.services.sha256_service import sha256_hex
from app.domain.value_objects.statuses import EvidenceItemType, EvidencePackageStatus
from app.shared.clock import format_date, utcnow
from app.shared.constants import (
    EVENT_TO_PACKAGE_TYPE,
    SCHEMA_VERSION_EVIDENCE_ITEM,
    SCHEMA_VERSION_EVIDENCE_PACKAGE,
)
from app.shared.ids import new_id


def _resolve_package_type(event: ProvenanceEvent, result_scope: str | None) -> str:
    mapped = EVENT_TO_PACKAGE_TYPE.get(event.event_type)
    if event.event_type == "CALCULATION_APPROVED":
        if result_scope == "monthly":
            return "monthly_carbon_result"
        if result_scope == "annual":
            return "annual_carbon_result"
    return mapped or "manual_audit_package"


def _build_item_payload(
    *,
    item_id: str,
    item_order: int,
    item_type: str,
    source_reference: str,
    core_hashes: dict,
    period: dict | None = None,
) -> dict:
    payload = {
        "core_hashes": core_hashes,
        "item_id": item_id,
        "item_order": item_order,
        "item_type": item_type,
        "schema_version": SCHEMA_VERSION_EVIDENCE_ITEM,
        "source_reference": source_reference,
    }
    if period:
        payload["period"] = period
    return payload


class EvidencePackageBuilder:
    def __init__(self, data_reader: ProvenanceDataReaderPort) -> None:
        self._data_reader = data_reader

    def build(
        self,
        *,
        anchor_request_id: UUID,
        event: ProvenanceEvent,
        public_summary_enabled: bool = False,
    ) -> tuple[EvidencePackage, list[EvidenceItem]]:
        result_set = None
        if event.calculation_result_set_id:
            result_set = self._data_reader.get_calculation_result_set(
                event.calculation_result_set_id
            )

        reporting_period_id = event.reporting_period_id
        if result_set and result_set.reporting_period_id:
            reporting_period_id = result_set.reporting_period_id

        period = self._data_reader.get_reporting_period(reporting_period_id) if reporting_period_id else None
        pipeline_run = (
            self._data_reader.get_pipeline_run(event.pipeline_run_id)
            if event.pipeline_run_id
            else None
        )
        if pipeline_run is None and result_set:
            pipeline_run = self._data_reader.get_pipeline_run(result_set.pipeline_run_id)

        period_start = format_date(period.period_start) if period else "1970-01-01"
        period_end = format_date(period.period_end) if period else "1970-01-01"
        period_granularity = period.period_granularity if period else "custom"
        period_block = {
            "period_end": period_end,
            "period_granularity": period_granularity,
            "period_start": period_start,
        }

        package_type = _resolve_package_type(
            event, result_set.result_scope if result_set else None
        )
        now = utcnow()
        package_id = new_id()
        items: list[EvidenceItem] = []
        order = 1

        if result_set:
            method_hash = self._data_reader.get_calculation_execution_method_version_hash(
                result_set.calculation_execution_id
            )
            if method_hash:
                item_id = str(new_id())
                payload = _build_item_payload(
                    item_id=item_id,
                    item_order=order,
                    item_type=EvidenceItemType.CALCULATION_METHOD_VERSION.value,
                    source_reference=str(result_set.calculation_execution_id),
                    core_hashes={"method_version_hash": method_hash},
                    period=period_block,
                )
                items.append(
                    EvidenceItem(
                        evidence_item_id=UUID(item_id),
                        evidence_package_id=package_id,
                        item_order=order,
                        item_type=EvidenceItemType.CALCULATION_METHOD_VERSION.value,
                        source_table="calculation_calculation_execution",
                        source_record_id=result_set.calculation_execution_id,
                        source_event_id=event.outbox_event_id,
                        source_hash_value=method_hash,
                        canonical_payload_json=to_canonical_json(payload),
                        item_hash=sha256_hex(payload),
                        created_at=now,
                    )
                )
                order += 1

            parameter_hash = self._data_reader.get_calculation_execution_parameter_set_hash(
                result_set.calculation_execution_id
            )
            if parameter_hash:
                item_id = str(new_id())
                payload = _build_item_payload(
                    item_id=item_id,
                    item_order=order,
                    item_type=EvidenceItemType.PARAMETER_SET.value,
                    source_reference=str(result_set.calculation_execution_id),
                    core_hashes={"parameter_set_hash": parameter_hash},
                    period=period_block,
                )
                items.append(
                    EvidenceItem(
                        evidence_item_id=UUID(item_id),
                        evidence_package_id=package_id,
                        item_order=order,
                        item_type=EvidenceItemType.PARAMETER_SET.value,
                        source_table="calculation_calculation_execution",
                        source_record_id=result_set.calculation_execution_id,
                        source_event_id=event.outbox_event_id,
                        source_hash_value=parameter_hash,
                        canonical_payload_json=to_canonical_json(payload),
                        item_hash=sha256_hex(payload),
                        created_at=now,
                    )
                )
                order += 1

            if result_set.summary_hash:
                item_id = str(new_id())
                payload = _build_item_payload(
                    item_id=item_id,
                    item_order=order,
                    item_type=EvidenceItemType.APPROVED_RESULT.value,
                    source_reference=str(result_set.calculation_result_set_id),
                    core_hashes={"summary_hash": result_set.summary_hash},
                    period=period_block,
                )
                items.append(
                    EvidenceItem(
                        evidence_item_id=UUID(item_id),
                        evidence_package_id=package_id,
                        item_order=order,
                        item_type=EvidenceItemType.APPROVED_RESULT.value,
                        source_table="calculation_calculation_result_set",
                        source_record_id=result_set.calculation_result_set_id,
                        source_event_id=event.outbox_event_id,
                        source_hash_value=result_set.summary_hash,
                        canonical_payload_json=to_canonical_json(payload),
                        item_hash=sha256_hex(payload),
                        created_at=now,
                    )
                )
                order += 1

        if event.source_record_id and event.event_type.endswith("_TO_ONTOLOGY"):
            publication_hash = event.payload.get("publication_payload_hash")
            item_id = str(new_id())
            payload = _build_item_payload(
                item_id=item_id,
                item_order=order,
                item_type=EvidenceItemType.PUBLICATION_RECEIPT.value,
                source_reference=str(event.source_record_id),
                core_hashes={"publication_payload_hash": publication_hash or "unknown"},
                period=period_block,
            )
            items.append(
                EvidenceItem(
                    evidence_item_id=UUID(item_id),
                    evidence_package_id=package_id,
                    item_order=order,
                    item_type=EvidenceItemType.PUBLICATION_RECEIPT.value,
                    source_table=event.source_table,
                    source_record_id=event.source_record_id,
                    source_event_id=event.outbox_event_id,
                    source_hash_value=publication_hash,
                    canonical_payload_json=to_canonical_json(payload),
                    item_hash=sha256_hex(payload),
                    created_at=now,
                )
            )
            order += 1

        if event.source_record_id and "AGGREGATED" in event.event_type:
            link = self._data_reader.get_aggregation_link_by_id(event.source_record_id)
            if link:
                item_id = str(new_id())
                payload = _build_item_payload(
                    item_id=item_id,
                    item_order=order,
                    item_type=EvidenceItemType.AGGREGATION_LINK.value,
                    source_reference=str(link.aggregation_link_id),
                    core_hashes={
                        "parent_result_set_id": str(link.parent_result_set_id),
                        "child_result_set_id": str(link.child_result_set_id),
                        "aggregation_type": link.aggregation_type,
                    },
                    period=period_block,
                )
                items.append(
                    EvidenceItem(
                        evidence_item_id=UUID(item_id),
                        evidence_package_id=package_id,
                        item_order=order,
                        item_type=EvidenceItemType.AGGREGATION_LINK.value,
                        source_table="calculation_result_aggregation_link",
                        source_record_id=link.aggregation_link_id,
                        source_event_id=event.outbox_event_id,
                        source_hash_value=None,
                        canonical_payload_json=to_canonical_json(payload),
                        item_hash=sha256_hex(payload),
                        created_at=now,
                    )
                )

        if not items:
            item_id = str(new_id())
            payload = _build_item_payload(
                item_id=item_id,
                item_order=1,
                item_type=EvidenceItemType.LOCAL_HASH_REF.value,
                source_reference=event.outbox_event_id,
                core_hashes={"event_type": event.event_type},
                period=period_block,
            )
            items.append(
                EvidenceItem(
                    evidence_item_id=UUID(item_id),
                    evidence_package_id=package_id,
                    item_order=1,
                    item_type=EvidenceItemType.LOCAL_HASH_REF.value,
                    source_table=event.source_table,
                    source_record_id=event.source_record_id,
                    source_event_id=event.outbox_event_id,
                    source_hash_value=None,
                    canonical_payload_json=to_canonical_json(payload),
                    item_hash=sha256_hex(payload),
                    created_at=now,
                )
            )

        merkle = build_merkle_root(
            [
                MerkleLeaf(
                    item_id=str(item.evidence_item_id),
                    item_order=item.item_order,
                    item_hash=item.item_hash or "",
                )
                for item in items
            ]
        )

        package_payload = {
            "evidence_items": [
                {
                    "item_hash": item.item_hash,
                    "item_id": str(item.evidence_item_id),
                    "item_order": item.item_order,
                    "item_type": item.item_type,
                }
                for item in items
            ],
            "integrity_context": {
                "canonicalization_method": "json_canonical_v1",
                "hash_algorithm": "sha256",
            },
            "package_id": str(package_id),
            "package_type": package_type,
            "package_version": "1.0.0",
            "period_end": period_end,
            "period_granularity": period_granularity,
            "period_start": period_start,
            "schema_version": SCHEMA_VERSION_EVIDENCE_PACKAGE,
            "scope": {
                "farm_id_hash": pipeline_run.farm_id_hash if pipeline_run else None,
                "management_unit_id_hash": None,
                "project_id_hash": pipeline_run.project_id_hash if pipeline_run else None,
            },
        }
        package_hash = sha256_hex(package_payload)
        metadata_payload = {
            "anchor_request_id": str(anchor_request_id),
            "event_type": event.event_type,
            "source_event_id": event.outbox_event_id,
        }
        metadata_hash = sha256_hex(metadata_payload)

        package = EvidencePackage(
            evidence_package_id=package_id,
            anchor_request_id=anchor_request_id,
            package_type=package_type,
            package_version="1.0.0",
            period_start=period_start,
            period_end=period_end,
            period_granularity=period_granularity,
            project_id_hash=pipeline_run.project_id_hash if pipeline_run else None,
            farm_id_hash=pipeline_run.farm_id_hash if pipeline_run else None,
            management_unit_id_hash=None,
            canonical_payload_json=to_canonical_json(package_payload),
            package_hash=package_hash,
            merkle_root=merkle.merkle_root,
            metadata_hash=metadata_hash,
            public_summary_enabled=public_summary_enabled,
            status=EvidencePackageStatus.READY_TO_ANCHOR.value,
            created_at=now,
            updated_at=now,
        )
        return package, items
