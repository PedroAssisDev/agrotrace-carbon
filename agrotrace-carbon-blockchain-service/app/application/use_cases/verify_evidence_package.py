from __future__ import annotations

import json

from app.application.dto.commands import VerifyEvidencePackageCommand
from app.application.dto.results import VerifyEvidencePackageResult
from app.domain.entities import VerificationLog
from app.domain.services.canonical_json_service import (
    DEFAULT_CANONICALIZATION_METHOD,
    UnknownCanonicalizationError,
    parse_canonical_json,
    resolve_canonicalization_method,
)
from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root
from app.domain.services.sha256_service import sha256_hex
from app.domain.value_objects.statuses import EvidencePackageStatus, VerificationType
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.clock import utcnow
from app.shared.exceptions import NotFoundError, VerificationError
from app.shared.ids import new_id


def _resolve_package_method(package, uow) -> str:
    """Read canonicalization_method from package / hash_record; default historical v1."""
    try:
        payload = parse_canonical_json(package.canonical_payload_json or "{}")
        integrity = payload.get("integrity_context") or {}
        method = integrity.get("canonicalization_method") or payload.get("canonicalization_method")
        if method:
            return resolve_canonicalization_method(method)
    except Exception:
        pass
    try:
        records = uow.hash_records.list_by_package(package.evidence_package_id)
        for rec in records or []:
            method = getattr(rec, "canonicalization_method", None)
            if method:
                return resolve_canonicalization_method(method)
    except Exception:
        pass
    return DEFAULT_CANONICALIZATION_METHOD


class VerifyEvidencePackageUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: VerifyEvidencePackageCommand) -> VerifyEvidencePackageResult:
        package = self._uow.evidence_packages.get(command.evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")

        try:
            method = _resolve_package_method(package, self._uow)
        except UnknownCanonicalizationError as exc:
            raise VerificationError(str(exc)) from exc

        items = self._uow.evidence_items.list_by_package(package.evidence_package_id)
        item_results: list[dict] = []
        all_items_valid = True
        computed_leaves: list[MerkleLeaf] = []

        for item in items:
            payload = parse_canonical_json(item.canonical_payload_json or "{}")
            computed = sha256_hex(payload, method=method)
            is_valid = computed == item.item_hash
            all_items_valid = all_items_valid and is_valid
            computed_leaves.append(
                MerkleLeaf(
                    item_id=str(item.evidence_item_id),
                    item_order=item.item_order,
                    item_hash=computed,
                )
            )
            self._uow.verification_logs.add(
                VerificationLog(
                    verification_log_id=new_id(),
                    evidence_package_id=package.evidence_package_id,
                    verification_type=VerificationType.ITEM_HASH.value,
                    expected_hash=item.item_hash,
                    computed_hash=computed,
                    is_valid=is_valid,
                    verified_at=utcnow(),
                    details_json=json.dumps(
                        {"item_id": str(item.evidence_item_id), "canonicalization_method": method}
                    ),
                )
            )
            item_results.append(
                {
                    "item_id": str(item.evidence_item_id),
                    "expected": item.item_hash,
                    "computed": computed,
                    "is_valid": is_valid,
                    "canonicalization_method": method,
                }
            )

        computed_package_hash = sha256_hex(
            parse_canonical_json(package.canonical_payload_json or "{}"),
            method=method,
        )
        package_hash_valid = computed_package_hash == package.package_hash
        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.PACKAGE_HASH.value,
                expected_hash=package.package_hash,
                computed_hash=computed_package_hash,
                is_valid=package_hash_valid,
                verified_at=utcnow(),
                details_json=json.dumps({"canonicalization_method": method}),
            )
        )

        computed_merkle = build_merkle_root(computed_leaves).merkle_root if computed_leaves else ""
        merkle_valid = computed_merkle == (package.merkle_root or "")
        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.MERKLE_ROOT.value,
                expected_hash=package.merkle_root,
                computed_hash=computed_merkle,
                is_valid=merkle_valid,
                verified_at=utcnow(),
                details_json=None,
            )
        )

        is_valid = all_items_valid and package_hash_valid and merkle_valid
        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.FULL.value,
                expected_hash=package.package_hash,
                computed_hash=computed_package_hash,
                is_valid=is_valid,
                verified_at=utcnow(),
                details_json=json.dumps({"item_count": len(items), "canonicalization_method": method}),
            )
        )

        package.status = (
            EvidencePackageStatus.VERIFIED.value
            if is_valid
            else EvidencePackageStatus.VERIFICATION_FAILED.value
        )
        package.updated_at = utcnow()
        self._uow.evidence_packages.update(package)

        self._audit.info(
            event_name="EVIDENCE_PACKAGE_VERIFIED" if is_valid else "EVIDENCE_PACKAGE_VERIFICATION_FAILED",
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Verification completed",
            context={"is_valid": is_valid, "canonicalization_method": method},
        )

        return VerifyEvidencePackageResult(
            evidence_package_id=package.evidence_package_id,
            is_valid=is_valid,
            details={
                "items": item_results,
                "package_hash_valid": package_hash_valid,
                "merkle_root_valid": merkle_valid,
                "canonicalization_method": method,
            },
        )
