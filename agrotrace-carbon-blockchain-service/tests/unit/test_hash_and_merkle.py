from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.services.canonical_json_service import (
    CanonicalizationError,
    canonicalize_value,
    to_canonical_json,
)
from app.domain.services.idempotency_service import build_idempotency_key
from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root, verify_merkle_root
from app.domain.services.sha256_service import sha256_hex


def test_canonical_json_is_deterministic() -> None:
    payload = {"b": 2, "a": {"d": 4, "c": 3}, "list": [2, 1]}
    first = to_canonical_json(payload)
    second = to_canonical_json({"list": [2, 1], "a": {"c": 3, "d": 4}, "b": 2})
    assert first == second
    assert first == '{"a":{"c":3,"d":4},"b":2,"list":[2,1]}'


def test_canonical_nested_and_unicode() -> None:
    payload = {"nome": "Café", "nested": {"z": 1, "a": [1, 2, {"k": "ü"}]}}
    assert to_canonical_json(payload) == to_canonical_json(
        {"nested": {"a": [1, 2, {"k": "ü"}], "z": 1}, "nome": "Café"}
    )


def test_canonical_null_and_bools() -> None:
    assert to_canonical_json({"a": None, "b": True, "c": False}) == '{"a":null,"b":true,"c":false}'


def test_canonical_dates() -> None:
    instant = datetime(2026, 1, 15, 12, 30, 0, tzinfo=UTC)
    result = to_canonical_json({"ts": instant, "d": instant.date()})
    assert '"ts":"2026-01-15T12:30:00Z"' in result
    assert '"d":"2026-01-15"' in result


def test_equivalent_numbers_canonicalize_alike() -> None:
    a = to_canonical_json({"v": 1})
    b = to_canonical_json({"v": 1.0})
    c = to_canonical_json({"v": Decimal("1.000")})
    assert a == b == c == '{"v":1}'


def test_numeric_string_differs_from_number() -> None:
    assert to_canonical_json({"v": "1.0"}) == '{"v":"1.0"}'
    assert to_canonical_json({"v": 1.0}) == '{"v":1}'
    assert sha256_hex({"v": "1.0"}) != sha256_hex({"v": 1.0})


def test_unsupported_type_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonicalize_value(object())


def test_sha256_is_deterministic() -> None:
    payload = {"schema_version": "evidence_item_v1", "item_id": "abc"}
    first = sha256_hex(payload)
    second = sha256_hex(payload)
    assert first == second
    assert first.startswith("0x")
    assert len(first) == 66


def test_idempotency_key_deterministic() -> None:
    key = build_idempotency_key("local_simulated", "0x" + "ab" * 32)
    assert key == build_idempotency_key("local_simulated", "0x" + "ab" * 32)
    assert key != build_idempotency_key("anvil_local", "0x" + "ab" * 32)
    assert key != build_idempotency_key("local_simulated", "0x" + "cd" * 32)


def test_merkle_root_is_deterministic() -> None:
    leaves = [
        MerkleLeaf(item_id="item-2", item_order=2, item_hash="0x" + "aa" * 32),
        MerkleLeaf(item_id="item-1", item_order=1, item_hash="0x" + "bb" * 32),
    ]
    first = build_merkle_root(leaves)
    second = build_merkle_root(leaves)
    assert first.merkle_root == second.merkle_root


def test_changing_item_changes_merkle_root() -> None:
    base = [
        MerkleLeaf(item_id="item-1", item_order=1, item_hash="0x" + "11" * 32),
        MerkleLeaf(item_id="item-2", item_order=2, item_hash="0x" + "22" * 32),
    ]
    changed = [
        MerkleLeaf(item_id="item-1", item_order=1, item_hash="0x" + "11" * 32),
        MerkleLeaf(item_id="item-2", item_order=2, item_hash="0x" + "33" * 32),
    ]
    assert build_merkle_root(base).merkle_root != build_merkle_root(changed).merkle_root


def test_odd_leaf_count_duplicates_last_node() -> None:
    leaves = [
        MerkleLeaf(item_id="item-1", item_order=1, item_hash="0x" + "11" * 32),
        MerkleLeaf(item_id="item-2", item_order=2, item_hash="0x" + "22" * 32),
        MerkleLeaf(item_id="item-3", item_order=3, item_hash="0x" + "33" * 32),
    ]
    result = build_merkle_root(leaves)
    assert verify_merkle_root(leaves, result.merkle_root)
