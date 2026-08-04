# Especificação do módulo de treinamento de modelos

## Objetivo

Construir um módulo independente para extrair resultados históricos aprovados, preparar conjuntos de dados, treinar modelos candidatos, selecionar os melhores modelos e registrar os artefatos necessários para uso futuro.

## Fora do escopo

- telas e frontend;
- callbacks do frontend;
- recebimento da expectativa futura de vacas em lactação (inferência);
- endpoints de inferência;
- execução de previsão para o usuário;
- aprovação de previsões;
- ancoragem em blockchain;
- leitura RDF/TTL da ontologia agromrv-lite (etapa posterior).

## Regras obrigatórias

### Dados

- Consumir somente resultados aprovados e publicados (quando as colunas de controle existirem).
- Não misturar granularidades mensal e anual em um mesmo treinamento.
- Não misturar resultados reais com previsões.
- Preservar `property_id`, `period` e `granularity` nos datasets auditáveis.
- Registrar hash SHA-256 do dataset usado em cada modelo.
- Caminhos relativos do YAML resolvem-se a partir do diretório do arquivo de configuração.

### Regressão

- Feature única: `lactating_cows`.
- Alvos independentes: `milk_production_liters`, `total_ghg_emissions_tco2e`.
- Modelos globais por granularidade (mensal e anual).
- **Regressão contemporânea aplicada a um cenário futuro:** treina `(vacas_X, alvo_X)` no mesmo período; não desloca o target.
- Baseline obrigatório: `mean_per_cow_baseline`.
- Complexos só vencem se melhorarem o baseline; empate favorece o modelo mais simples.
- Validação: GroupKFold (≥3 propriedades), LeaveOneGroupOut (2), holdout cronológico sem shuffle (1).
- Não adicionar área, vacas secas, clima, energia ou outras features.

### Série temporal

- Granularidade: mensal.
- Escopo: uma propriedade por modelo.
- Série univariada, sem variáveis exógenas e sem `lactating_cows`.
- Horizonte: três meses.
- Baseline principal: `naive`.
- Lacunas: `reject` ou `skip_property` (sem interpolação).
- Mínimo padrão: 12 observações consecutivas.

### Datasets

- Mensal/anual global: usados na regressão.
- Mensal por propriedade: usado nas séries (em memória).
- Anual por propriedade: **somente auditoria**.

### Avaliação e seleção

- Métrica configurável: `mae` (padrão) ou `rmse`.
- `minimum_improvement_over_baseline` com tolerância float documentada `0.0` (comparação estrita).
- Registrar comparação vencedor versus baseline.

### Artefatos

Cada modelo deve possuir modelo serializado, metadados (incl. rastreabilidade), métricas, parâmetros, manifesto, cópia dos dados, versão e entrada no registro.

Por execução: `resolved_config.json`, `training_environment.json`, `last_training_report.json`.

### LSTM

- Experimental, desativada por padrão; não candidata padrão; sem carregamento TensorFlow quando desligada.

## Critérios de aceite

- `pytest` executa sem falhas.
- O comando `train-all` processa o CSV de exemplo.
- São gerados modelos de regressão mensal e anual para os dois alvos.
- São gerados modelos temporais mensais para propriedades com histórico suficiente.
- Nenhum modelo temporal utiliza `lactating_cows`.
- Nenhum modelo de regressão utiliza outra feature além de `lactating_cows`.
