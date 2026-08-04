# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O `agrotrace-carbon-model-training-service` (pacote `carbonseco-model-training-service`, import `model_training_service`) está instalável de forma standalone via `pip install -e ".[dev]"`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `.gitignore` | OK — `.env`, `models/`, `artifacts/**`, venv, caches |
| `.env.example` | Criado (config canônica em `configs/training.yaml`) |
| `pyproject.toml` v1.0.0 | Versão bump 0.1.0 → 1.0.0 |
| `__version__ = "1.0.0"` | `model_training_service/__init__.py` |
| Testes (`pytest -q`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- Artefatos de treino em `artifacts/` e dados processados permanecem locais/ignorados; não fazem parte do pacote distribuível.
- Extra opcional `lstm` (TensorFlow) permanece experimental e desativado por padrão.

## Instalação standalone

```bash
cd agrotrace-carbon-model-training-service
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -e ".[dev]"
pip check
pytest -q
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e resultado de `pip check`.
