# IMPLEMENTACAO_ETHEREUM_SEPOLIA

## 21.1 Resumo executivo

Foi implementada a evolução do `agrotrace-carbon-blockchain-service` para ancoragem EVM real, preservando o fluxo simulado existente.

| Aspecto | Estado |
|---|---|
| O que continua simulado | `local_simulated` / `SimulatedAnchorProvider` (default) |
| O que passou a ser real | Contrato `CarbonEvidenceRegistry`, `EvmAnchorProvider`, Anvil (testado), Sepolia (código + scripts; execução externa pendente de credenciais) |
| Gate | Somente publicação final (`FINAL_ONTOLOGY_PUBLISHED` e aliases) |
| Canonicalização | Única oficial: `json_canonical_v1` |
| Idempotência | `SHA-256(network_code:package_hash)` com UNIQUE em SQLite |
| Anvil | Integração automatizada passando (`pytest -m blockchain_local`) |
| Sepolia | Provider/config/CLI/smoke prontos; testes marcados `sepolia` skipped sem `RUN_SEPOLIA_TESTS=1` |

## 21.2 Arquivos alterados

| arquivo | tipo | responsabilidade |
|---|---|---|
| `app/shared/constants.py` | alterado | eventos elegíveis finais + network codes |
| `app/shared/exceptions.py` | alterado | `FinalPublicationRequiredError`, erros EVM |
| `app/shared/config.py` | alterado | settings Anvil/Sepolia |
| `app/domain/services/canonical_json_service.py` | alterado | canonicalização endurecida |
| `app/domain/services/final_publication_gate.py` | novo | gate de publicação final |
| `app/domain/services/idempotency_service.py` | novo | chave idempotente |
| `app/domain/ports/blockchain_anchor_provider_port.py` | alterado | query DTOs/porta |
| `app/domain/entities/__init__.py` | alterado | `idempotency_key` |
| `app/domain/value_objects/statuses.py` | alterado | statuses EVM + verification on-chain |
| `app/application/use_cases/anchor_evidence_package.py` | novo | UC geral de ancoragem |
| `app/application/use_cases/simulate_anchoring.py` | alterado | wrapper compatível |
| `app/application/use_cases/query_anchored_evidence.py` | novo | consulta on-chain |
| `app/application/use_cases/verify_anchored_evidence.py` | novo | verify off+on-chain |
| `app/application/use_cases/create_anchor_request.py` | alterado | gate |
| `app/application/use_cases/build_evidence_package.py` | alterado | gate |
| `app/application/use_cases/verify_evidence_package.py` | alterado | Merkle a partir de hashes recomputados |
| `app/application/dto/commands.py` / `results.py` | alterado | DTOs EVM |
| `app/application/container.py` | alterado | registry com settings + migração |
| `app/infrastructure/anchoring/providers_registry.py` | alterado | lazy Anvil/Sepolia |
| `app/infrastructure/anchoring/evm/*` | novo | client/provider/hash/key/errors |
| `app/infrastructure/anchoring/contracts/*.abi.json` | novo | ABI versionada |
| `app/infrastructure/db/models.py` | alterado | coluna idempotency |
| `app/infrastructure/db/repositories/*` | alterado | CRUD idempotency + list verification |
| `schemas/sqlite/blockchain_service_schema.sql` | alterado | DDL |
| `scripts/migrate_add_idempotency_key.py` | novo | migração segura |
| `scripts/export_contract_abi.py` | novo | export ABI |
| `scripts/sepolia_smoke_test.py` | novo | smoke Sepolia |
| `contracts/**` | novo | Solidity + Foundry + deploy |
| `app/interfaces/cli/__main__.py` | alterado | anchor/query/verify |
| `frontend/services/blockchain_adapter.py` | alterado | rede + metadados EVM |
| `frontend/services/blockchain_view_service.py` | alterado | resumo EVM/explorador |
| `frontend/components/blockchain_anchor_card.py` | alterado | UI SIMULADA vs EVM |
| `frontend/utils/hash_helpers.py` | alterado | hash oficial via serviço |
| `frontend/services/direct_imports.py` | alterado | novos use cases |
| `frontend/services/local_orchestrator.py` | alterado | ancoragem por rede |
| `frontend/config.py` | alterado | `BLOCKCHAIN_DEFAULT_NETWORK_CODE` |
| `docs/*` | alterado/novo | integração EVM/segurança |
| `.env.example` | novo | placeholders |
| `.gitignore` | alterado | artifacts Foundry |

## 21.3 Decisões arquiteturais

- **Provider genérico:** um `EvmAnchorProvider` + configs Anvil/Sepolia (sem duplicação).
- **Portas:** `BlockchainAnchorProviderPort` estendida com `BlockchainAnchorQueryPort` opcional.
- **Idempotência:** aplicação + persistência UNIQUE; provider EVM também rejeita overwrite on-chain.
- **Canonicalização:** única em `canonical_json_service.py`; frontend importa `sha256_hex` oficial.
- **Contrato:** owner imutável, anti-overwrite, anti-zero, evento `EvidenceAnchored`.
- **Persistência:** SQLite mantido; campos EVM em colunas existentes + `response_payload_json` estruturado + `idempotency_key`.
- **Compatibilidade:** `simulate-anchoring` e `SimulateAnchoringUseCase` preservados.

## 21.4 Contrato

`CarbonEvidenceRegistry`

- Funções: `anchorEvidence`, `getEvidence`, `evidenceExists`, `owner`
- Evento: `EvidenceAnchored(evidenceKey, packageHash, merkleRoot, submitter, anchoredAt)`
- Erros: `NotAuthorized`, `ZeroEvidenceKey`, `ZeroPackageHash`, `ZeroMerkleRoot`, `EvidenceAlreadyAnchored`
- Acesso: somente `owner` (constructor)
- Sobrescrita: proibida
- `evidenceKey = keccak256(UTF-8(evidence_package_id))`
- `packageHash` / `merkleRoot`: bytes32 diretos do SHA-256 oficial

## 21.5 Configuração

Variáveis (somente nomes):

```text
BLOCKCHAIN_DEFAULT_NETWORK_CODE
BLOCKCHAIN_ANVIL_RPC_URL
BLOCKCHAIN_ANVIL_CHAIN_ID
BLOCKCHAIN_ANVIL_PRIVATE_KEY
BLOCKCHAIN_ANVIL_CONTRACT_ADDRESS
BLOCKCHAIN_ANVIL_CONFIRMATIONS
BLOCKCHAIN_ANVIL_REQUEST_TIMEOUT_SECONDS
BLOCKCHAIN_ANVIL_RECEIPT_TIMEOUT_SECONDS
BLOCKCHAIN_SEPOLIA_RPC_URL
BLOCKCHAIN_SEPOLIA_CHAIN_ID
BLOCKCHAIN_SEPOLIA_PRIVATE_KEY
BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS
BLOCKCHAIN_SEPOLIA_CONFIRMATIONS
BLOCKCHAIN_SEPOLIA_REQUEST_TIMEOUT_SECONDS
BLOCKCHAIN_SEPOLIA_RECEIPT_TIMEOUT_SECONDS
BLOCKCHAIN_SEPOLIA_EXPLORER_BASE_URL
RUN_SEPOLIA_TESTS
```

## 21.6 Testes

| suite | quantidade | resultado | tempo | observações |
|---|---|---|---|---|
| Python pytest (completo) | 37 passed + 1 skipped | OK | ~15s | Sepolia skipped |
| Foundry `forge test` | 9 passed | OK | <1s | CarbonEvidenceRegistry |
| Anvil `blockchain_local` | 3 passed | OK | ~12s | subprocess Anvil + deploy real |
| Sepolia `sepolia` | 1 skipped | skipped | — | sem credenciais / `RUN_SEPOLIA_TESTS` |

## 21.7 Anvil

Validado automaticamente pelos testes de integração:

- chain ID: `31337`
- deploy local via bytecode Foundry + Web3
- transação real com recibo `status=1`
- consulta on-chain com `packageHash`/`merkleRoot` iguais aos locais
- idempotência: segunda chamada retorna `idempotent_reuse=true` sem novo envio
- terceira tentativa direta no provider → `DuplicateEvidenceError`

Endereços/tx hashes são efêmeros por execução local (Anvil efêmero).

## 21.8 Sepolia

**Não executada nesta sessão.** Motivo: variáveis `BLOCKCHAIN_SEPOLIA_*` não configuradas e `RUN_SEPOLIA_TESTS` ausente.

Não foram inventados endereço de contrato, hash de deploy ou transação Sepolia.

Manifesto placeholder: `contracts/deployments/sepolia.json` (`status: not_deployed`).

## 21.9 Pendências

1. Configurar RPC/chave/contrato Sepolia e executar deploy real
2. Preencher `contracts/deployments/sepolia.json` com valores reais pós-deploy
3. Rodar `scripts/sepolia_smoke_test.py` com um `package-id` existente
4. Opcional: `RUN_SEPOLIA_TESTS=1` na CI local com segredos externos

## 21.10 Como reproduzir

```bash
# Dependências
cd agrotrace-carbon-blockchain-service
python -m pip install -e ".[dev]"
python -m pip install "web3>=6.20.0,<8"

# Testes Python
python -m pytest tests/ -q

# Foundry
cd contracts
forge build
forge test -vvv
forge fmt --check

# Anvil automático
cd ..
python -m pytest tests/integration/test_anvil_anchoring.py -m blockchain_local -vv

# Anvil manual
anvil --host 127.0.0.1 --port 8545 --chain-id 31337
# (outro terminal) forge create ... --broadcast
python -m app.interfaces.cli anchor-package --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli query-anchor --package-id <UUID> --network-code anvil_local

# Sepolia (quando configurado)
# copiar .env.example → .env e preencher
forge script script/DeployCarbonEvidenceRegistry.s.sol --rpc-url "$BLOCKCHAIN_SEPOLIA_RPC_URL" --private-key "$BLOCKCHAIN_SEPOLIA_PRIVATE_KEY" --broadcast
python scripts/sepolia_smoke_test.py --package-id <UUID>
python -m app.interfaces.cli verify-anchor --package-id <UUID> --network-code ethereum_sepolia
```
