"""Official canonicalization for evidence hashes: json_canonical_v1.

This is the single source of truth for generating official package/item hashes.
Frontend and other modules must import these functions rather than reimplementing.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.shared.clock import format_instant


class CanonicalizationError(ValueError):
    """Raised when a value cannot be safely canonicalized."""


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
