"""Shared golden-vector tests for json_canonical_v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.services.canonical_json_service import (
    UnknownCanonicalizationError,
    to_canonical_json,
    to_canonical_json_for,
)
from app.domain.services.sha256_service import sha256_hex

VECTORS_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "canonical"
    / "canonical_vectors.json"
)


@pytest.fixture(scope="module")
def vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def test_vectors_file_present(vectors: dict) -> None:
    assert vectors["strategy"] == "json_canonical_v1"
    assert len(vectors["vectors"]) >= 5


def test_key_order_equal(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "key_order_equal")
    a, b = entry["payloads"]
    assert to_canonical_json(a) == to_canonical_json(b) == entry["canonical_bytes"]
    assert sha256_hex(a) == sha256_hex(b) == entry["hash"]


def test_unicode_accents(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "unicode_accents")
    payload = entry["payloads"][0]
    assert to_canonical_json(payload) == entry["canonical_bytes"]
    assert "São" in entry["canonical_bytes"] or "S\\u00e3o" not in entry["canonical_bytes"]
    assert sha256_hex(payload) == entry["hash"]


def test_value_alteration_diverges(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "value_alteration_diverges")
    a, b = entry["payloads"]
    assert sha256_hex(a) != sha256_hex(b)
    assert [sha256_hex(a), sha256_hex(b)] == entry["hashes"]


def test_list_order_matters(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "list_order_matters")
    a, b = entry["payloads"]
    assert to_canonical_json(a) != to_canonical_json(b)


def test_null_bool_numbers(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "null_bool_numbers")
    payload = entry["payloads"][0]
    canonical = to_canonical_json(payload)
    assert canonical == entry["canonical_bytes"]
    assert '"n":null' in canonical
    assert '"t":true' in canonical
    assert '"i":1' in canonical
    # 1.0 normalizes to int 1
    assert '"w":1' in canonical


def test_unknown_method_raises(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "unknown_method_raises")
    with pytest.raises(UnknownCanonicalizationError):
        to_canonical_json_for(entry["method"], {"a": 1})


def test_missing_method_defaults_v1(vectors: dict) -> None:
    entry = next(v for v in vectors["vectors"] if v["id"] == "missing_method_defaults_v1")
    assert to_canonical_json_for(None, {"a": 1}) == entry["canonical_bytes"]
    assert to_canonical_json_for("", {"a": 1}) == entry["canonical_bytes"]
