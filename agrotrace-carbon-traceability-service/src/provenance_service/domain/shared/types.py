"""Value objects shared across contexts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from provenance_service.domain.shared.enums import HashAlgorithm

_HEX_RE = re.compile(r"^[0-9a-f]+$")
_BUSINESS_KEY_RE = re.compile(r"^[A-Za-z0-9_.:\-/]{1,255}$")
_IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")


@dataclass(frozen=True, slots=True)
class Hash:
    """A pair of (algorithm, hex digest)."""

    algorithm: HashAlgorithm
    value: str

    def __post_init__(self) -> None:
        if not _HEX_RE.match(self.value):
            raise ValueError(f"Hash value must be lowercase hex: {self.value!r}")
        expected = 64
        if len(self.value) != expected:
            raise ValueError(
                f"Hash value length {len(self.value)} does not match {expected} expected for "
                f"{self.algorithm.value}"
            )

    def to_string(self) -> str:
        return f"{self.algorithm.value}:{self.value}"


@dataclass(frozen=True, slots=True)
class BusinessKey:
    """A natural, human-readable identifier of an aggregate."""

    value: str

    def __post_init__(self) -> None:
        if not _BUSINESS_KEY_RE.match(self.value):
            raise ValueError(f"BusinessKey {self.value!r} does not match {_BUSINESS_KEY_RE.pattern}")


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """An opaque idempotency token supplied by the caller."""

    value: str

    def __post_init__(self) -> None:
        if not _IDEMPOTENCY_KEY_RE.match(self.value):
            raise ValueError(
                f"IdempotencyKey {self.value!r} does not match {_IDEMPOTENCY_KEY_RE.pattern}"
            )
