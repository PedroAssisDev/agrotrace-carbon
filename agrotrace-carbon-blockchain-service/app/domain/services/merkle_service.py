from __future__ import annotations

from dataclasses import dataclass

from app.domain.services.sha256_service import hash_bytes, normalize_hash_to_bytes, sha256_hex
from app.shared.constants import MERKLE_STRATEGY_V1


@dataclass(frozen=True, slots=True)
class MerkleLeaf:
    item_id: str
    item_order: int
    item_hash: str


@dataclass(frozen=True, slots=True)
class MerkleTreeResult:
    merkle_root: str
    leaf_hashes: list[str]
    strategy: str = MERKLE_STRATEGY_V1


def build_merkle_root(leaves: list[MerkleLeaf]) -> MerkleTreeResult:
    if not leaves:
        raise ValueError("At least one leaf is required to build a Merkle tree")

    ordered = sorted(leaves, key=lambda leaf: (leaf.item_order, leaf.item_id))
    level = [normalize_hash_to_bytes(leaf.item_hash) for leaf in ordered]
    leaf_hashes = [f"0x{value.hex()}" for value in level]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[bytes] = []
        for index in range(0, len(level), 2):
            next_level.append(hash_bytes(level[index], level[index + 1]))
        level = next_level

    return MerkleTreeResult(merkle_root=f"0x{level[0].hex()}", leaf_hashes=leaf_hashes)


def verify_merkle_root(leaves: list[MerkleLeaf], expected_root: str) -> bool:
    computed = build_merkle_root(leaves)
    return computed.merkle_root.lower() == expected_root.lower()
