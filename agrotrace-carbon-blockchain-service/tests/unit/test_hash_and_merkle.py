from __future__ import annotations

from app.domain.services.canonical_json_service import to_canonical_json
from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root, verify_merkle_root
from app.domain.services.sha256_service import sha256_hex


def test_canonical_json_is_deterministic() -> None:
    payload = {"b": 2, "a": {"d": 4, "c": 3}, "list": [2, 1]}
    first = to_canonical_json(payload)
    second = to_canonical_json({"list": [2, 1], "a": {"c": 3, "d": 4}, "b": 2})
    assert first == second
    assert first == '{"a":{"c":3,"d":4},"b":2,"list":[2,1]}'


def test_sha256_is_deterministic() -> None:
    payload = {"schema_version": "evidence_item_v1", "item_id": "abc"}
    first = sha256_hex(payload)
    second = sha256_hex(payload)
    assert first == second
    assert first.startswith("0x")


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
