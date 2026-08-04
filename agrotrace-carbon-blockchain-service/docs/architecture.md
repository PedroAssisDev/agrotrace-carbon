# Architecture

## Clean Architecture layers

- `domain`: entities, value objects, canonical hash/Merkle/idempotency services, ports, final publication gate
- `application`: use cases and orchestration
- `infrastructure`: SQLite repositories, provenance readers, simulated + EVM anchor providers
- `interfaces`: CLI and worker
- `shared`: settings, constants, clock, ids, exceptions
- `contracts/`: Foundry Solidity (`CarbonEvidenceRegistry`)

## Flow

1. `ObserveProvenanceEventsUseCase` reads **final publication** events from provenance outbox
2. Observer / `CreateAnchorRequestUseCase` creates `anchor_request`
3. `BuildEvidencePackageUseCase` composes evidence items and hashes (gate enforced)
4. `AnchorEvidencePackageUseCase` applies idempotency and submits via provider registry
5. `SimulateAnchoringUseCase` remains a compatibility wrapper for `local_simulated`
6. `VerifyEvidencePackageUseCase` recomputes off-chain integrity
7. `QueryAnchoredEvidenceUseCase` / `VerifyAnchoredEvidenceUseCase` compare on-chain records

## Providers

```text
ProvidersRegistry (lazy)
├── local_simulated → SimulatedAnchorProvider
├── anvil_local → EvmAnchorProvider(anvil config)
└── ethereum_sepolia → EvmAnchorProvider(sepolia config)
```

Web3 is never opened at import time.

## Boundaries

- Provenance service remains source of truth for lineage
- Blockchain service remains source of truth for evidence packages and anchoring attempts
- Blockchain stores only cryptographic evidence (hashes), never business payloads
- No HTTP API between frontend and this service — direct Python imports only
