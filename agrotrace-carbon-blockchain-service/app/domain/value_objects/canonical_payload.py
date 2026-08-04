from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeterministicHash:
    value: str
    algorithm: str
    canonicalization_method: str

    def __post_init__(self) -> None:
        if not self.value.startswith("0x"):
            raise ValueError("Hash value must start with 0x prefix")


@dataclass(frozen=True, slots=True)
class CanonicalPayload:
    schema_version: str
    payload: dict
