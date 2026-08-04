# Relatório de validação — consolidação + ajustes

Data: 2026-07-22.

## Testes

```bash
python -m pytest -v --tb=line
```

Resultado:

```text
41 passed in 48.79s
```

## Pipeline de exemplo (MAE)

```bash
python -m model_training_service.cli train-all \
  --csv examples/approved_results.csv \
  --config configs/training.yaml
```

Expectativa: 10 modelos (4 regressão + 6 séries), `data_source.type=csv`, feature única, horizonte 3, LSTM desligada.
