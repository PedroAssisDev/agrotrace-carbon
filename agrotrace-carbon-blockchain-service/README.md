# Agrotrace Carbon Blockchain Service

Observa a publicação final, monta pacotes de evidência, gera hashes/Merkle e ancora —
em modo simulado ou EVM (Anvil / Sepolia).

> Documento canônico do monorepo: [../docs/modules/blockchain-service.md](../docs/modules/blockchain-service.md)

## Gate

Somente após publicação final (`FINAL_ONTOLOGY_PUBLISHED` / aliases). O frontend aplica
`is_blockchain_unlocked()` e `pipeline_guards` antes de evidência/ancoragem/verificação.

## Responsabilidades

- Observar eventos elegíveis do ledger de proveniência
- Criar `anchor_request`, `evidence_package` e itens **somente após publicação final**
- Payload canônico (`json_canonical_v1`), `package_hash`, `merkle_root` (SHA-256)
- Ancorar via `local_simulated`, `anvil_local` ou `ethereum_sepolia`
- Verificar integridade off-chain (e on-chain no caminho EVM)
- Persistência em `$AGROTRACE_DATA_ROOT/db/blockchain_service.db` + arquivos de pacote

## Providers

```text
BlockchainAnchorProviderPort
├── SimulatedAnchorProvider   (local_simulated)     ← default
└── EvmAnchorProvider         (anvil_local, ethereum_sepolia)  ← preparado
```

## Setup

```bash
pip install -e ".[dev]"
python -m app.interfaces.cli init-db
```

Variáveis: `.env.example` (nunca versione segredos).

## CLI (standalone)

```bash
python -m app.interfaces.cli observe-events
python -m app.interfaces.cli build-evidence-package --event-id <outbox_event_id>
python -m app.interfaces.cli simulate-anchoring --package-id <UUID>
python -m app.interfaces.cli anchor-package --package-id <UUID> --network-code local_simulated
python -m app.interfaces.cli verify-package --package-id <UUID>
```

No Dash, o fluxo equivalente passa por `frontend/services/blockchain_adapter.py` e o
orquestrador pós-aprovação.

## Contrato Solidity

```bash
cd contracts
forge build
forge test -vvv
```

## Testes

```bash
python -m pytest tests/ -q -m "not blockchain_local and not sepolia"
python -m pytest tests/ -m blockchain_local -q
# Sepolia só com config explícita:
# RUN_SEPOLIA_TESTS=1 python -m pytest tests/ -m sepolia
```

## Documentação

| Documento | Papel |
|-----------|-------|
| [docs/ethereum_integration.md](docs/ethereum_integration.md) | Visão dos providers |
| [docs/sepolia_deployment.md](docs/sepolia_deployment.md) | Guia operacional Sepolia (canônico) |
| [docs/anvil_local_validation.md](docs/anvil_local_validation.md) | Anvil local |
| [docs/architecture.md](docs/architecture.md) | Arquitetura do serviço |
| [docs/hash_strategy.md](docs/hash_strategy.md) | Hashes / idempotência |
| Changelog histórico | [../docs/evidence/blockchain/IMPLEMENTACAO_ETHEREUM_SEPOLIA.md](../docs/evidence/blockchain/IMPLEMENTACAO_ETHEREUM_SEPOLIA.md) |

Guia longo histórico: [`../docs/archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md`](../docs/archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md).
Prefira `docs/sepolia_deployment.md` + o changelog em `docs/evidence/blockchain/`.
