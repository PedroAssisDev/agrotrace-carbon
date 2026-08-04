# Módulo: model-training-service

## Finalidade

Produzir estimativas preditivas de emissões/produção (modelos treinados), separadas do
cálculo oficial.

## Responsabilidades

- Treinar modelos e registrá-los; gerar estimativas preditivas.
- Manter um registry de modelos.

## Não faz

- Não substitui o cálculo oficial. Predição **não** é publicável nem ancorável.

## Contratos e execução

- CLI: `model_training_service.cli`.
- Integração no frontend via página `/previsoes` e serviços de previsão.
- Bloqueio de publicação: `publication_service._reject_prediction_input`
  (`PredictionNotPublishableError`).

## Entradas / saídas / persistência

- Entrada: séries/exemplos (`examples/`).
- Saída: modelos e estimativas em `artifacts/` (**gerado**); registry em
  `artifacts/registry.jsonl` (`MODEL_REGISTRY_PATH`).

## Configuração

- Caminhos em `frontend/config.py`: `MODEL_TRAINING_SERVICE_DIR`,
  `MODEL_TRAINING_ARTIFACTS_DIR`, `MODEL_REGISTRY_PATH`.
- Config de treino: `configs/training.yaml`.

## Testes e comandos

- `pytest` no serviço; `validate_forecast_page`, `validate_prediction_separation`.

## Relacionados

- RF011; CE3.
- Detalhe: `agrotrace-carbon-model-training-service/README.md` (spec/análise arquivados
  em prompts/relatórios do serviço). Prompt de geração:
  [../archive/prompts/model-training-CURSOR_PROMPT.md](../archive/prompts/model-training-CURSOR_PROMPT.md).
