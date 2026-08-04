# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-blockchain-service` (import `app`) está instalável de forma standalone via `pip install -e ".[dev]"`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | Criado — venv, `.env`, `*.db`, `*-wal`, `*-shm`, `evidence/**`, cache, out, broadcast |
| `pyproject.toml` v1.0.0 | Versão bump 0.1.0 → 1.0.0 |
| `jsonschema` runtime (P9) | Promovido de `dev` para dependências principais |
| `__version__ = "1.0.0"` | `app/__init__.py` |
| Testes (`pytest -m "not blockchain_local and not sepolia" -q`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- **ABI/schema legacy removal deferred:** `resolve_abi_path()` ainda aceita `CarbonEvidenceRegistry.abi.json` legado; remoção formal na fase de legado.
- Arquivos já rastreados em `evidence/`, `*.db` ou similares **não foram removidos** — apenas ignorados para novos artefatos.
- Testes `blockchain_local` (Anvil) e `sepolia` exigem infraestrutura externa e ficam fora do gate de packaging desta fase.

## Instalação standalone

```bash
cd agrotrace-carbon-blockchain-service
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -e ".[dev]"
pip check
pytest tests/ -m "not blockchain_local and not sepolia" -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
