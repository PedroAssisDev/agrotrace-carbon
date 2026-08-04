# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-wrappers-service` está instalável de forma standalone via `pip install -e .` (fonte canônica: `pyproject.toml`).

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | Criado (venv, caches, build artifacts, `.env`) |
| `pyproject.toml` v1.0.0 | Criado — deps runtime: PyYAML, pandas; extra `test`: pytest |
| `__version__ = "1.0.0"` | Adicionado em `__init__.py` |
| `requirements.txt` | Mantido, alinhado ao pyproject com nota de fonte canônica |
| Testes (`pytest -q`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- **`process_file_auto`** permanece na API pública até a fase de remoção de legado; produção deve preferir `process_file(uri, layout_id)`.
- Pacote PyPI interno exposto como import **`wrappers`** (alias histórico do monorepo).

## Instalação standalone

```bash
cd agrotrace-carbon-wrappers-service
python -m venv .venv-test
.venv-test\Scripts\activate   # Windows
pip install -e ".[test]"
pip check
pytest -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
