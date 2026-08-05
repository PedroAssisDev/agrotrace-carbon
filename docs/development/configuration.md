# Configuração

Flags em `frontend/config.py`:

| Flag | Valor esperado (fluxo real) |
|------|-----------------------------|
| `USE_DIRECT_FUNCTION_CALLS` | `True` |
| `USE_MOCK_DATA` | `False` |
| `ALLOW_MOCK_FALLBACK` | `False` (falha explícita) |

## Variáveis de ambiente (somente nomes)

Fonte: `.env.example` na raiz (nunca versione `.env` com segredos).

| Variável | Finalidade | Obrigatória |
|----------|------------|-------------|
| `AGROTRACE_DATA_ROOT` | Raiz dos artefatos operacionais (padrão `frontend/data/`) | Não (tem default) |
| `AGROTRACE_LOG_LEVEL` | Nível de log | Não |
| `AGROTRACE_LOG_FILE` | Arquivo de log | Não |
| `BLOCKCHAIN_DEFAULT_NETWORK_CODE` | Provider default (`local_simulated`) | Não |
| `BLOCKCHAIN_CONTRACT_NAME` / `VERSION` / `ABI_CHECKSUM_SHA256` | Metadados do contrato | Para EVM |
| `BLOCKCHAIN_ANVIL_*` | RPC, chain ID, chave, endereço (Anvil) | Para `anvil_local` |
| `BLOCKCHAIN_SEPOLIA_*` | RPC, chain ID, chave, endereço, confirmações | Para `ethereum_sepolia` |

Definidas pelo bootstrap a partir do data root (quando não override):

- `PROV_DATABASE_URL`
- `BLOCKCHAIN_DATABASE_URL`
- `BLOCKCHAIN_PROVENANCE_DATABASE_URL`

## Modelos preditivos (`/previsoes`)

| Constante | Padrão |
|-----------|--------|
| `MODEL_TRAINING_SERVICE_DIR` | `WORKSPACE_ROOT / agrotrace-carbon-model-training-service` |
| `MODEL_TRAINING_ARTIFACTS_DIR` | `…/artifacts` |
| `MODEL_REGISTRY_PATH` | `…/artifacts/registry.jsonl` |

Ver também: [data-directories.md](data-directories.md), [../limitations.md](../limitations.md).
