# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-ontology-manager` (pacote `agromrv-o-lite`, import `ontology`) está instalável de forma standalone via `pip install -e .`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | Criado |
| `pyproject.toml` v1.0.0 | Versão bump 0.1.0 → 1.0.0 |
| `__version__ = "1.0.0"` | Adicionado em `ontology/__init__.py` |
| Classe `Lot` | Confirmada em `ontology/schema.py` (sem duplicação) |
| Testes (`pytest -q`) | Ver `results.json` |

## Limitações conhecidas

- Nome de distribuição PyPI interno permanece **`agromrv-o-lite`** (histórico); diretório do monorepo: `agrotrace-carbon-ontology-manager`.
- `requires-python >=3.9` mantido (compatível com owlready2/rdflib).

## Instalação standalone

```bash
cd agrotrace-carbon-ontology-manager
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -e ".[dev]"
pip check
pytest -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
