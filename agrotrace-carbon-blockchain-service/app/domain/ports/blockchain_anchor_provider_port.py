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
