# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-calculation-service` (pacote `ecofarm-calculations`, imports `emissions` / `orchestration`) está instalável de forma standalone via `pip install -e .`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | Criado |
| `pyproject.toml` v1.0.0 | Versão bump 0.3.0 → 1.0.0; build-system setuptools |
| `__version__ = "1.0.0"` | Adicionado em `emissions/__init__.py` |
| Testes (`pytest -q`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- **`TemporalScope.YEARLY`** mantido como alias de leitura legada (`YEARLY = "annual"`) até migração formal para `ANNUAL` na fase de remoção de legado.
- Pacotes importáveis permanecem na raiz do serviço (`emissions`, `orchestration`), não renomeados.

## Instalação standalone

```bash
cd agrotrace-carbon-calculation-service
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -e ".[test]"
pip check
pytest -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
