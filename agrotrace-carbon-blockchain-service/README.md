# Agrotrace Carbon Blockchain Service

Serviço responsável por observar eventos do `agrotrace-carbon-traceability-service`, montar pacotes de evidência, gerar hashes determinísticos, Merkle Roots e ancorar evidências criptográficas — em modo simulado ou em redes EVM (Anvil / Sepolia).

> Documento canônico do módulo: [../docs/modules/blockchain-service.md](../docs/modules/blockchain-service.md).

## Responsabilidades

- Observar `audit_outbox_event` do serviço de proveniência
- Criar `anchor_request`, `evidence_package` e `evidence_item` **somente após publicação final**
- Gerar payload canônico (`json_canonical_v1`), `package_hash` e `merkle_root` (SHA-256)
- Ancorar via `local_simulated`, `anvil_local` ou `ethereum_sepolia`
- Verificar integridade off-chain e on-chain
- Manter banco SQLite próprio + trilha de auditoria

## Providers

```text
BlockchainAnchorProviderPort
├── SimulatedAnchorProvider   (local_simulated)
└── EvmAnchorProvider         (anvil_local, ethereum_sepolia)
```

## Setup

```bash
pip install -e ".[dev]"
python -m app.interfaces.cli init-db
```

See `.env.example` for configuration names (never commit secrets).

## Comandos CLI

```bash
python -m app.interfaces.cli observe-events
python -m app.interfaces.cli process-anchor-requests
python -m app.interfaces.cli build-evidence-package --event-id <outbox_event_id>
python -m app.interfaces.cli simulate-anchoring --package-id <UUID>
python -m app.interfaces.cli anchor-package --package-id <UUID> --network-code local_simulated
python -m app.interfaces.cli anchor-package --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli query-anchor --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli verify-anchor --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli verify-package --package-id <UUID>
```

## Contrato Solidity

```bash
cd contracts
forge build
forge test -vvv
```

## Testes

```bash
python -m pytest tests/ -q
python -m pytest tests/ -m blockchain_local -q
# Sepolia (somente com configuração explícita):
# RUN_SEPOLIA_TESTS=1 python -m pytest tests/ -m sepolia
```

## Documentação

- `docs/architecture.md`
- `docs/ethereum_integration.md`
- `docs/anvil_local_validation.md`
- `docs/sepolia_deployment.md`
- `docs/security_and_secrets.md`
- `docs/hash_strategy.md`
- `schemas/canonical/canonicalization_rules.md`
