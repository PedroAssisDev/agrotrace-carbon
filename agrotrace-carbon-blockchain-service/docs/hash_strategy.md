# Hash Strategy

## Canonicalization

- Method: `json_canonical_v1`
- **Official implementation:** `app/domain/services/canonical_json_service.py`
- Recursive lexicographic key ordering
- Compact JSON (`separators=(',', ':')`)
- UTC timestamps with `Z`
- Deterministic number normalization (`1` / `1.0` / `Decimal("1.000")` → same form)
- Numeric strings stay strings
- Scaled integers for optional public emission values

Frontend UI artifact hashes may use local helpers for display, but **official evidence
package / item hashes** must use the blockchain-service canonicalization + `sha256_hex`.

## SHA-256

- Input: UTF-8 bytes of canonical JSON
- Output: lowercase hex with `0x` prefix (`0x` + 64 chars)
- Do **not** replace SHA-256 with Keccak for official hashes
- Do **not** hash the hexadecimal string again before storing on-chain — convert
  `0x…` hex directly to `bytes32`

## On-chain evidence key

```text
evidenceKey = keccak256(UTF-8(evidence_package_id))
```

This identifies the package on-chain. `packageHash` and `merkleRoot` remain SHA-256 digests.

## Idempotency key

```text
idempotency_key = SHA-256(network_code + ":" + package_hash)
```

Same network + same package hash must not create a second on-chain submission.

## Volatile fields excluded

- processing timestamps
- retry counters
- lock metadata
- internal status fields
