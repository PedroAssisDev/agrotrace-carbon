"""Recompute and verify hash records against persisted ledger subjects."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from provenance_service.application.unit_of_work import UnitOfWork
from provenance_service.domain.audit.hash_payloads import (
    calculation_parameter_set_hash_from_entities,
    calculation_result_set_hash_from_entities,
    canonical_snapshot_hash_from_entities,
)
from provenance_service.domain.shared.enums import HashAlgorithm, HashSubjectKind
from provenance_service.domain.shared.errors import NotFoundError


@dataclass(slots=True)
class HashCheckResult:
    subject_kind: str
    subject_id: UUID
    expected_hash: str
    actual_hash: str | None
    matches: bool
    verification_mode: str
    mirror_hash: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class IntegrityReport:
    bundle_id: UUID
    pipeline_run_id: UUID
    is_valid: bool
    checks: list[HashCheckResult] = field(default_factory=list)
    missing_subjects: list[UUID] = field(default_factory=list)
    unsupported_subjects: list[UUID] = field(default_factory=list)


class VerifyIntegrity:
    def __init__(self, uow_factory) -> None:
        self._uow_factory = uow_factory

    def execute(self, bundle_id: UUID) -> IntegrityReport:
        with self._uow_factory() as uow:
            bundle = uow.prov_bundles.get(bundle_id)
            if bundle is None:
                raise NotFoundError(f"ProvBundle {bundle_id} not found")

            report = IntegrityReport(
                bundle_id=bundle_id,
                pipeline_run_id=bundle.pipeline_run_id,
                is_valid=True,
            )

            hash_records = [
                hr
                for hr in uow.hash_records.list_by_pipeline_run(bundle.pipeline_run_id)
                if hr.bundle_id is None or hr.bundle_id == bundle_id
            ]

            for hash_record in hash_records:
                algorithm = hash_record.hash_algorithm
                recomputed, mode, detail = self._recompute(
                    uow, hash_record.subject_kind, hash_record.subject_id, algorithm
                )
                mirror = self._mirror_hash(
                    uow, hash_record.subject_kind, hash_record.subject_id
                )

                if mode == "skipped":
                    report.unsupported_subjects.append(hash_record.subject_id)
                    matches = mirror == hash_record.hash_value if mirror else False
                    actual = mirror
                elif recomputed is None:
                    report.missing_subjects.append(hash_record.subject_id)
                    matches = False
                    actual = None
                else:
                    actual = recomputed
                    matches = recomputed == hash_record.hash_value
                    if mirror is not None and mirror != recomputed:
                        matches = False
                        detail = (detail or "") + "; mirror_mismatch"

                report.checks.append(
                    HashCheckResult(
                        subject_kind=hash_record.subject_kind.value,
                        subject_id=hash_record.subject_id,
                        expected_hash=hash_record.hash_value,
                        actual_hash=actual,
                        matches=matches,
                        verification_mode=mode,
                        mirror_hash=mirror,
                        detail=detail,
                    )
                )
                if not matches:
                    report.is_valid = False

            return report

    def _recompute(
        self,
        uow: UnitOfWork,
        subject_kind: HashSubjectKind,
        subject_id: UUID,
        algorithm: HashAlgorithm,
    ) -> tuple[str | None, str, str | None]:
        if subject_kind is HashSubjectKind.CANONICAL_SNAPSHOT:
            snap = uow.canonical_snapshots.get(subject_id)
            if snap is None:
                return None, "recomputed", "subject_not_found"
            items = uow.canonical_snapshots.list_items(subject_id)
            from provenance_service.domain.shared.hashing import compute_hash_hex

            h = canonical_snapshot_hash_from_entities(snap, items)
            if algorithm is not HashAlgorithm.SHA256:
                h = compute_hash_hex(
                    {
                        "graph_name": snap.graph_name,
                        "snapshot_label": snap.snapshot_label,
                        "schema_version": snap.schema_version,
                        "payload": snap.payload,
                        "items": [
                            {"item_key": i.item_key, **dict(i.payload)}
                            for i in sorted(items, key=lambda x: x.item_key)
                        ],
                    },
                    algorithm=algorithm,
                )
            return h, "recomputed", None

        if subject_kind is HashSubjectKind.CALCULATION_PARAMETER_SET:
            ps = uow.calculation_parameter_sets.get(subject_id)
            if ps is None:
                return None, "recomputed", "subject_not_found"
            values = uow.calculation_parameter_sets.list_values(subject_id)
            return calculation_parameter_set_hash_from_entities(ps, values), "recomputed", None

        if subject_kind is HashSubjectKind.CALCULATION_RESULT_SET:
            rs = uow.calculation_result_sets.get(subject_id)
            if rs is None:
                return None, "recomputed", "subject_not_found"
            items = uow.calculation_result_sets.list_items(subject_id)
            return calculation_result_set_hash_from_entities(rs, items), "recomputed", None

        if subject_kind in (
            HashSubjectKind.SOURCE_ARTIFACT,
            HashSubjectKind.SOURCE_ARTIFACT_REVISION,
            HashSubjectKind.NORMALIZED_BATCH,
        ):
            mirror = self._mirror_hash(uow, subject_kind, subject_id)
            return mirror, "mirror", "external_content_hash"

        if subject_kind in (HashSubjectKind.BUNDLE, HashSubjectKind.OTHER):
            return None, "skipped", "no_canonical_payload"

        return None, "skipped", f"unsupported_kind:{subject_kind.value}"

    def _mirror_hash(
        self, uow: UnitOfWork, subject_kind: HashSubjectKind, subject_id: UUID
    ) -> str | None:
        kind = subject_kind.value
        if subject_kind is HashSubjectKind.SOURCE_ARTIFACT:
            artifact = uow.source_artifacts.get(subject_id)
            return artifact.content_hash if artifact else None
        if subject_kind is HashSubjectKind.SOURCE_ARTIFACT_REVISION:
            revision = uow.source_artifact_revisions.get(subject_id)
            return revision.content_hash if revision else None
        if subject_kind is HashSubjectKind.NORMALIZED_BATCH:
            batch = uow.normalized_batches.get(subject_id)
            return batch.content_hash if batch else None
        if subject_kind is HashSubjectKind.CANONICAL_SNAPSHOT:
            snapshot = uow.canonical_snapshots.get(subject_id)
            return snapshot.snapshot_hash if snapshot else None
        if subject_kind is HashSubjectKind.CALCULATION_RESULT_SET:
            result_set = uow.calculation_result_sets.get(subject_id)
            return result_set.summary_hash if result_set else None
        if subject_kind is HashSubjectKind.CALCULATION_PARAMETER_SET:
            param_set = uow.calculation_parameter_sets.get(subject_id)
            if param_set is None:
                return None
            entity = uow.prov_entities.get(param_set.prov_entity_id)
            return entity.content_hash if entity else None
        if subject_kind is HashSubjectKind.BUNDLE:
            return None
        if subject_kind is HashSubjectKind.OTHER:
            return None
        return None
