from __future__ import annotations

from uuid import UUID

from app.domain.services.canonical_json_service import parse_canonical_json
from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root
from app.domain.services.sha256_service import sha256_hex
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.exceptions import NotFoundError


class GenerateItemHashUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def execute(self, evidence_item_id: UUID) -> str:
        item = self._uow.evidence_items.get(evidence_item_id)
        if item is None:
            raise NotFoundError(f"Evidence item not found: {evidence_item_id}")
        payload = parse_canonical_json(item.canonical_payload_json or "{}")
        item_hash = sha256_hex(payload)
        item.item_hash = item_hash
        self._uow.evidence_items.update(item)
        return item_hash


class GeneratePackageHashUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def execute(self, evidence_package_id: UUID) -> str:
        package = self._uow.evidence_packages.get(evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {evidence_package_id}")
        payload = parse_canonical_json(package.canonical_payload_json or "{}")
        package_hash = sha256_hex(payload)
        package.package_hash = package_hash
        self._uow.evidence_packages.update(package)
        return package_hash


class GenerateMerkleRootUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def execute(self, evidence_package_id: UUID) -> str:
        package = self._uow.evidence_packages.get(evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {evidence_package_id}")
        items = self._uow.evidence_items.list_by_package(evidence_package_id)
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
        package.merkle_root = merkle.merkle_root
        self._uow.evidence_packages.update(package)
        return merkle.merkle_root
