# Ethereum Integration

## Simulated vs real

| Mode | `network_code` | Provider | On-chain |
|---|---|---|---|
| Simulated | `local_simulated` | `SimulatedAnchorProvider` | No — synthetic tx/block |
| Anvil | `anvil_local` | `EvmAnchorProvider` | Yes — local chain 31337 |
| Sepolia | `ethereum_sepolia` | `EvmAnchorProvider` | Yes — chain 11155111 |

Default remains `local_simulated` via `BLOCKCHAIN_DEFAULT_NETWORK_CODE`.

## Architecture

```text
BlockchainAnchorProviderPort
├── SimulatedAnchorProvider
└── EvmAnchorProvider (Anvil + Sepolia configs)
```

`ProvidersRegistry` constructs EVM providers lazily — imports never open RPC.

Use cases:

- `AnchorEvidencePackageUseCase` — general anchoring + idempotency + final publication gate
- `SimulateAnchoringUseCase` — compatibility wrapper
- `QueryAnchoredEvidenceUseCase` / `VerifyAnchoredEvidenceUseCase`

## Off-chain vs on-chain

**Off-chain (SQLite):** evidence package, items, canonical JSON, SHA-256 hashes, Merkle root, audit trail, verification log.

**On-chain (bytes32 only):**

- `evidenceKey = keccak256(UTF-8(evidence_package_id))`
- `packageHash` — official SHA-256 of canonical manifesto (`0x` hex → bytes32, no re-hash)
- `merkleRoot` — official Merkle root

Never send property data, PII, or full payloads on-chain.

## Idempotency

`idempotency_key = SHA-256(network_code + ":" + package_hash)`

Same network + same package hash returns the existing transaction without a new send.

## Gate

Only final publication events create/anchor packages:

- `FINAL_ONTOLOGY_PUBLISHED`
- `APPROVED_RESULT_PUBLISHED`
- `APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY`
