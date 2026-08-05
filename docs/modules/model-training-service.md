# Módulo: model-training-service

## Visão geral

Gerar, avaliar, selecionar e versionar modelos preditivos. A **inferência** na UI não
roda neste pacote — fica em `frontend/services/forecast_inference/`.

**Posição:** fora do ciclo MRV oficial (página `/previsoes`). Predição **não** é
publicável nem ancorável.

## Responsabilidades

- Treinar/avaliar/versionar regressão e séries temporais
- Manter registry de modelos

## Não faz

- Não substitui o cálculo oficial
- Não publica resultados preditivos no manifesto

## Contratos

| Papel | Onde |
|-------|------|
| Treino | `ModelTrainingFacade` via `model_training_adapter.py` |
| Inferência UI | `frontend/services/forecast_inference/` |
| Bloqueio publicação | `publication_service` → `PredictionNotPublishableError` |

## Entradas / saídas / persistência

- Config: `configs/training.yaml`
- Artefatos: `artifacts/` ou `$AGROTRACE_DATA_ROOT/model_training/`
- Registry: `registry.jsonl`

## Classificação

| Recurso | Classe |
|---------|--------|
| Regressão / séries | Implementado |
| Inferência FE | Parcial (depende de artefatos) |
| LSTM | Desabilitada (`enable_lstm: false`) |

## Testes

`pytest`; `validate_forecast_page`, `validate_prediction_separation`.

## Relacionados

- RF011; CE3
- README: `agrotrace-carbon-model-training-service/README.md`
- Prompt histórico: [../archive/prompts/model-training-CURSOR_PROMPT.md](../archive/prompts/model-training-CURSOR_PROMPT.md)
