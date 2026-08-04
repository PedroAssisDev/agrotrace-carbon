# CarbonSECO Model Training Service

Módulo responsável **somente pela geração, avaliação, seleção e versionamento de modelos**. A execução de previsões pelo frontend ou por outro componente de inferência não faz parte deste projeto.

## Escopo definido

### Regressão (contemporânea aplicada a um cenário futuro)

- Treina com vacas em lactação e alvo **no mesmo período X**.
- Em uso futuro (fora deste módulo), o modelo recebe a quantidade *esperada* de vacas e estima produção/emissão para esse mesmo período futuro.
- Entrada exclusiva: `lactating_cows`.
- Alvos separados: `milk_production_liters`, `total_ghg_emissions_tco2e`.
- Modelos globais por granularidade: mensal e anual.
- Não desloca o target para o período seguinte.

### Séries temporais

- Somente dados mensais, univariados, por propriedade.
- Não usam `lactating_cows` nem variáveis exógenas.
- Horizonte registrado: **três meses**.
- Mínimo padrão: 12 observações mensais consecutivas.

### LSTM

- Experimental e **desativada** por padrão (`enable_lstm: false`).
- Com `false`, nenhuma dependência TensorFlow é carregada.
- Com `true`, o pipeline apenas registra um skip explícito (ainda não integrada).

## Fluxo do módulo

```text
CSV canônico (ou SPARQL genérico configurável)
        ↓
Filtro de resultados aprovados/publicados
        ↓
Validação e padronização
        ↓
Materialização dos datasets auditáveis
        ↓
Treinamento dos modelos candidatos + baselines
        ↓
Seleção com política explícita contra baseline
        ↓
Registro do modelo, métricas, metadados, ambiente e hash
```

## Datasets materializados

| Dataset | Uso no treinamento |
|---|---|
| Mensal global | Regressão mensal |
| Anual global | Regressão anual |
| Mensal por propriedade | Séries temporais (via dados em memória) |
| Anual por propriedade | **Somente auditoria** — sem consumidor nesta versão |

## Configuração

Arquivo: `configs/training.yaml`.

- Caminhos relativos em `paths.*` são resolvidos **em relação ao diretório do YAML**, não ao CWD do terminal.
  No arquivo padrão (`configs/training.yaml`), use `../artifacts` e `../data/processed` para gravar na raiz do módulo.
- `selection.metric`: `mae` (padrão) ou `rmse`.
- `selection.minimum_improvement_over_baseline`: melhoria estrita exigida sobre o baseline (padrão `0.0`; tolerância float documentada = `0.0`).
- `validation.monthly_gap_policy`: `reject` ou `skip_property` (sem interpolação).
- `regression.candidate_profile`: `core` ou `extended`.

### Política de validação (regressão)

| Propriedades | Estratégia |
|---|---|
| ≥ 3 | `GroupKFold` |
| 2 | `LeaveOneGroupOut` |
| 1 | Holdout cronológico (sem shuffle) |

### Política de seleção

- Regressão: baseline `mean_per_cow_baseline` sempre participa.
- Séries: baseline `naive` sempre participa.
- Complexos só vencem se melhorarem o baseline; empate favorece o modelo mais simples.

## Instalação

```bash
python -m venv .venv
# .venv\Scripts\activate         # Windows
source .venv/bin/activate        # Linux/macOS
pip install -e ".[dev]"
```

## Executar com o CSV de exemplo

```bash
model-training train-all \
  --csv examples/approved_results.csv \
  --config configs/training.yaml
```

Alternativa:

```bash
PYTHONPATH=src python -m model_training_service.cli train-all \
  --csv examples/approved_results.csv \
  --config configs/training.yaml
```

## SPARQL

Fonte HTTP genérica disponível. A consulta deve retornar o schema canônico. A integração real com a ontologia agromrv-lite (RDF/TTL) **não** faz parte desta versão.

## Artefatos gerados

```text
artifacts/
├── resolved_config.json
├── training_environment.json
├── last_training_report.json
├── registry.jsonl
├── regression/.../<versão>/
│   ├── model.joblib
│   ├── metadata.json
│   ├── metrics.json
│   ├── dataset_manifest.json
│   └── training_data.csv
└── time_series/monthly/<property>/<target>/<versão>/
    ├── model.joblib
    ├── metadata.json
    ├── metrics.json
    ├── dataset_manifest.json
    ├── training_series.csv
    └── validation_predictions.csv
```

### Consumo pelo frontend

Este serviço **não executa inferência** na UI. O frontend Dash:

1. lê `registry.jsonl` / `active_models.json` via `forecast_inference` para prever;
2. solicita criação/retreinamento via **`ModelTrainingFacade`** (`model_training_service.api`) — in-process, sem HTTP.

A CLI (`train-all`) também usa a fachada.
## Testes

```bash
pytest
```

## Arquivos de referência

- `PROJECT_SPEC.md`: especificação funcional e técnica.
- `.cursor/rules/model-training-service.mdc`: regras obrigatórias para alterações futuras.
