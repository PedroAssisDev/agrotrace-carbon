# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-traceability-service` (pacote `agrotrace-carbon-provenance-service`, import `provenance_service`) está instalável de forma standalone via `pip install -e ".[dev]"`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | OK — `.env`, `*.db`, venv, caches, logs |
| `pyproject.toml` v1.0.0 | Versão bump 0.1.0 → 1.0.0 |
| `__version__ = "1.0.0"` | `provenance_service/__init__.py` |
| Testes (`pytest -q`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- **`include_legacy`** é preocupação do frontend (filtro global / rotas); não há flag equivalente no serviço de proveniência nesta fase.
- Prefixos de schema/tabela legados (PostgreSQL) permanecem documentados em `ARCHITECTURE.md` por compatibilidade de nomenclatura.
- API HTTP FastAPI permanece disponível; integração canônica do protótipo é import direto via adapters do frontend.

## Instalação standalone

```bash
cd agrotrace-carbon-traceability-service
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -e ".[dev]"
pip check
pytest -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
