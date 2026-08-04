"""Official canonicalization for evidence hashes: json_canonical_v1.

This is the single source of truth for generating official package/item hashes.
Frontend and other modules must import these functions rather than reimplementing.

Versioned registry
------------------
``CANONICALIZATION_METHODS`` maps method name → serializer. Verification of
historical packages MUST dispatch via ``to_canonical_json_for(method, payload)``.
Unknown methods raise ``UnknownCanonicalizationError`` (fail closed).
Packages without a stored method default to ``json_canonical_v1`` (historical).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from app.shared.clock import format_instant

CANONICALIZATION_METHOD_V1 = "json_canonical_v1"
CANONICALIZATION_VERSION_V1 = "1"
DEFAULT_CANONICALIZATION_METHOD = CANONICALIZATION_METHOD_V1


class CanonicalizationError(ValueError):
    """Raised when a value cannot be safely canonicalized."""


class UnknownCanonicalizationError(CanonicalizationError):
    """Raised when a stored/requested canonicalization method is not registered."""


def _normalize_number(value: int | float | Decimal) -> int | str:
    """Normalize semantically equivalent numbers to a stable form.

    Integers and whole floats/Decimals become int.
    Non-integer decimals become a fixed decimal string without scientific notation.
    """
    if isinstance(value, bool):
        # bool is a subclass of int; treat explicitly elsewhere
        raise CanonicalizationError("boolean must be handled before number normalization")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            raise CanonicalizationError("NaN is not allowed in canonical JSON")
        if value in (float("inf"), float("-inf")):
            raise CanonicalizationError("Infinity is not allowed in canonical JSON")
        if value.is_integer():
            return int(value)
        # Avoid scientific notation divergence
        return format(value, "f").rstrip("0").rstrip(".") or "0"
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal is not allowed")
        if value == value.to_integral_value():
            return int(value)
        normalized = format(value, "f").rstrip("0").rstrip(".") or "0"
        return normalized
    raise CanonicalizationError(f"unsupported number type: {type(value)!r}")


def canonicalize_value(value: Any) -> Any:
    """Recursively canonicalize a value for json_canonical_v1."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # Numeric-looking strings remain strings (never coerced to numbers)
        return value
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return _normalize_number(value)
    if isinstance(value, datetime):
        return format_instant(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): canonicalize_value(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, (list, tuple)):
        return [canonicalize_value(item) for item in value]
    raise CanonicalizationError(
        f"unsupported type for json_canonical_v1: {type(value).__name__}"
    )


def to_canonical_json(payload: dict) -> str:
    """Serialize a dict to the official canonical JSON string (UTF-8 safe)."""
    if not isinstance(payload, dict):
        raise CanonicalizationError("canonical payload root must be a dict")
    canonical = canonicalize_value(payload)
    return json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def parse_canonical_json(payload_json: str) -> dict:
    """Parse a canonical JSON string back to a dict."""
    loaded = json.loads(payload_json)
    if not isinstance(loaded, dict):
        raise CanonicalizationError("canonical payload root must be an object")
    return loaded


# Registry of official methods. Only add a new entry when introducing a new
# versioned strategy; never silently change the semantics of an existing key.
CANONICALIZATION_METHODS: dict[str, Callable[[dict], str]] = {
    CANONICALIZATION_METHOD_V1: to_canonical_json,
}


def resolve_canonicalization_method(method: str | None) -> str:
    """Resolve stored method; None/empty → historical default json_canonical_v1."""
    if method is None or str(method).strip() == "":
        return DEFAULT_CANONICALIZATION_METHOD
    return str(method).strip()


def to_canonical_json_for(method: str | None, payload: dict) -> str:
    """Dispatch canonicalization by method name.

    - Unknown method → ``UnknownCanonicalizationError`` (fail closed).
    - Missing/None method → ``json_canonical_v1`` (historical packages).
    """
    resolved = resolve_canonicalization_method(method)
    fn = CANONICALIZATION_METHODS.get(resolved)
    if fn is None:
        raise UnknownCanonicalizationError(
            f"unknown canonicalization method: {resolved!r}; "
            f"known={sorted(CANONICALIZATION_METHODS)}"
        )
    return fn(payload)


def official_strategy_fields() -> dict[str, str]:
    """Fields for VersionManifest / evidence metadata."""
    return {
        "canonicalization_strategy": CANONICALIZATION_METHOD_V1,
        "canonicalization_version": CANONICALIZATION_VERSION_V1,
        "canonicalization_method": CANONICALIZATION_METHOD_V1,
    }
