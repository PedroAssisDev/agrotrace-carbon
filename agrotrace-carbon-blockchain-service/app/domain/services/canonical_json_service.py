from __future__ import annotations

import json
from typing import Any


def canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): canonicalize_value(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [canonicalize_value(item) for item in value]
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return format(value, "f").rstrip("0").rstrip(".") or "0"
    return value


def to_canonical_json(payload: dict) -> str:
    canonical = canonicalize_value(payload)
    return json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def parse_canonical_json(payload_json: str) -> dict:
    return json.loads(payload_json)
