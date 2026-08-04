from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AnchorSubmitRequest:
    evidence_package_id: UUID
    package_hash: str
    merkle_root: str
    metadata_hash: str
    anchor_payload_json: str


@dataclass(frozen=True, slots=True)
class AnchorSubmitResult:
    transaction_hash: str
    block_number: int
    anchored_at: datetime
    anchoring_status: str
    response_payload: dict


@dataclass(frozen=True, slots=True)
class AnchorQueryRequest:
    evidence_package_id: UUID
    package_hash: str | None = None
    merkle_root: str | None = None


@dataclass(frozen=True, slots=True)
class AnchorQueryResult:
    found: bool
    evidence_key: str | None
    package_hash: str | None
    merkle_root: str | None
    anchored_at: int | None
    submitter: str | None
    network_code: str
    chain_id: int | None
    contract_address: str | None


class BlockchainAnchorProviderPort(ABC):
    @abstractmethod
    def submit(self, request: AnchorSubmitRequest) -> AnchorSubmitResult:
        raise NotImplementedError

    @property
    @abstractmethod
    def network_code(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_type(self) -> str:
        raise NotImplementedError


class BlockchainAnchorQueryPort(ABC):
    """Optional query port for EVM providers (architectural extension)."""

    @abstractmethod
    def query(self, request: AnchorQueryRequest) -> AnchorQueryResult:
        raise NotImplementedError
