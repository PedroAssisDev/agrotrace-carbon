# Merkle Tree / Merkle Strategy

## Strategy

- Version: `merkle_strategy_v1`
- Leaves ordered by `item_order`, tie-break by `item_id`
- Leaf value: bytes of `item_hash` without `0x`
- Parent node: `sha256(left || right)` (SHA-256, not Keccak)
- Odd leaf count: duplicate last leaf at current level

## Storage

- `evidence_package.merkle_root` (official SHA-256, `0x` + 64 hex)
- On-chain: same digest converted directly to `bytes32`

## Verification

1. Recompute each `item_hash` from canonical item payload (`json_canonical_v1`)
2. Rebuild Merkle tree from **recomputed** leaf hashes
3. Compare with stored `merkle_root`
4. Optionally compare with on-chain `merkleRoot` via `VerifyAnchoredEvidenceUseCase`

## Relation to package hash

- `package_hash`: SHA-256 of the package manifesto canonical JSON
- `merkle_root`: Merkle over item hashes
- Both are anchored on-chain; neither is re-hashed before storage as `bytes32`
