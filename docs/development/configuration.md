# Configuração

Flags em `frontend/config.py`:

| Flag | Valor esperado (fluxo real) |
|------|-----------------------------|
| `USE_DIRECT_FUNCTION_CALLS` | `True` |
| `USE_MOCK_DATA` | `False` |
| `ALLOW_MOCK_FALLBACK` | `False` (falha explícita) |

Caminhos de modelos preditivos (página `/previsoes`):

| Constante | Padrão |
|-----------|--------|
| `MODEL_TRAINING_SERVICE_DIR` | `WORKSPACE_ROOT / agrotrace-carbon-model-training-service` |
| `MODEL_TRAINING_ARTIFACTS_DIR` | `…/artifacts` |
| `MODEL_REGISTRY_PATH` | `…/artifacts/registry.jsonl` |

Env relevantes (definidos pelo bootstrap):

- `PROV_DATABASE_URL`
- `BLOCKCHAIN_DATABASE_URL`
- `BLOCKCHAIN_PROVENANCE_DATABASE_URL`
- `AGROTRACE_LOG_LEVEL` / `AGROTRACE_LOG_FILE`
