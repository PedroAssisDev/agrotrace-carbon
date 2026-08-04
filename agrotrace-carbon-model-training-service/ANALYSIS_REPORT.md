# Relatório de análise inicial — model-training-service

Análise pedida por `CURSOR_PROMPT.md`. Nenhuma alteração de código de produção foi feita nesta etapa.

Data: 2026-07-16.

## Testes automatizados

Pré-requisito no ambiente atual: o venv do monorepo não tinha as dependências do módulo (`scikit-learn`, `joblib`, `statsmodels`, etc.). Foi necessário:

```bash
pip install -e ".[dev]"
```

Comando executado:

```bash
pytest
```

Resultado:

```text
5 passed in 36.20s
```

Cobertura funcional exercitada pelos testes:

- normalização e filtro de dados aprovados/publicados;
- rejeição de períodos duplicados;
- regressão usando somente `lactating_cows`;
- série temporal univariada com horizonte de três meses;
- execução completa com materialização de datasets e registro de artefatos.

## 1. O que já está implementado

| Área | Estado | Onde |
|------|--------|------|
| Fonte CSV + filtro approved/published | OK | `src/model_training_service/data/csv_source.py`, `validation.py` |
| Fonte SPARQL genérica (HTTP) | Stub funcional | `src/model_training_service/data/sparql_source.py` + `queries/approved_results.rq.example` |
| Dataset auditável + hash SHA-256 | OK | `dataset_builder.py`, `registry/artifact_store.py` |
| Regressão só `lactating_cows`, 2 alvos, monthly/annual | OK | `src/model_training_service/regression/` |
| Série temporal mensal univariada por propriedade, horizonte 3 | OK | `time_series/`, `evaluation/temporal.py` |
| Seleção por MAE + comparação com baselines | OK | trainers + candidates |
| CLI `train-all` (CSV ou SPARQL) | OK | `cli.py` |
| Testes das regras obrigatórias | OK | `tests/` (4 arquivos / 5 testes) |
| LSTM | Experimental, desligada por padrão | `experimental/lstm_forecaster.py` |

Critérios de aceite da `PROJECT_SPEC.md` para o caminho CSV estão cobertos pelo design e pelos testes: `pytest` passa; o fluxo materializa regressões mensal/anual para os dois alvos e séries temporais mensais por propriedade quando há histórico suficiente; regressão não usa outra feature além de `lactating_cows`; série temporal não inclui `lactating_cows` no treino.

Relatório prévio de execução de exemplo (`VALIDATION_REPORT.md`): `train-all` com CSV gerou 10 modelos (4 regressões + 6 séries), sem erros. Essa execução de exemplo não foi repetida nesta análise (escopo = pytest + relatório).

## 2. O que falta para conectar SPARQL à ontologia real (agromrv-lite)

A query de exemplo (`queries/approved_results.rq.example`) usa um modelo fictício `ex:ApprovedResult`. A ontologia real (`agrotrace-carbon-ontology-manager` / export `frontend/data/ontology_exports/agromrv_lite.ttl`) segue outro formato: registros (`MonthlyPropertyRecord`, `AnnualPropertyInventoryRecord`, etc.) com observações por variável.

Gaps concretos:

1. **Modelo de dados diferente** — valores vêm de `Observation` ligadas a `DataRecord` / `Property` / `TemporalContext` (`hasNumericValue`, `observesVariable`, `hasStartDate`, `hasTemporalGranularity`), não de uma classe `ApprovedResult`.
2. **Nomes canônicos divergentes** — o módulo espera `milk_production_liters` e `total_ghg_emissions_tco2e`; a ontologia usa `milk_production` / `total_milk_production` e `total_ghg_co2e`.
3. **Granularidade** — módulo: `monthly` / `annual`; ontologia: `month` / `year` em `hasTemporalGranularity`.
4. **Formato longo vs largo** — o TTL tem uma observação por variável; o módulo precisa de uma linha por `(property_id, period, granularity)` com as três métricas pivotadas.
5. **Aprovação/publicação ausentes na ontologia** — não há `approval_status` / `publication_status` no TTL. O gate `FINAL_ONTOLOGY_PUBLISHED` vive no ciclo do frontend (`publication_service`, `cycle_state`). Treinar “só aprovados/publicados” exige regra externa (ex.: só consumir export pós-publicação), não filtro SPARQL puro na ontologia atual.
6. **Endpoint SPARQL** — o monorepo exporta TTL/OWL; não há Fuseki/endpoint padrão. `SparqlApprovedResultsSource` só fala HTTP e não lê arquivo local.
7. **Tensão com a arquitetura do monorepo** — as rules do repositório pedem chamada direta Python (sem HTTP entre módulos). Uma fonte local RDF (arquivo TTL + SPARQL in-process) encaixa melhor que `--sparql-endpoint http://localhost:...`, mantendo a query configurável (regra do módulo: não acoplar IRIs no domínio).

Conexão mínima futura (fora desta análise): query SPARQL alinhada ao agromrv-lite + pós-processamento (mapear granularidade/variáveis + pivot) + política explícita de “aprovado/publicado” + fonte local ou endpoint documentado.

## 3. Possíveis inconsistências com a especificação

- A query de exemplo **não** é agromrv-lite (placeholder consciente no README; ainda assim bloqueia o fluxo SPARQL real).
- Aliases em `data/schema.py` cobrem alguns nomes CSV, mas **não** os canônicos da ontologia (`milk_production`, `total_ghg_co2e`, `month`/`year`).
- A spec exige treino só com resultados aprovados e publicados; na prática isso funciona no CSV de exemplo, **não** na ontologia exportada (sem metadados de aprovação).
- Indentação irregular no dict de config de `tests/test_training_service.py` (linhas do bloco `regression`); cosmético — Python aceita.
- `resolve_paths_relative_to_config` em `orchestration/training_service.py` é no-op: paths relativos dependem do CWD de execução.
- Dependências do módulo não estavam instaladas no venv do monorepo até `pip install -e ".[dev]"`; o README do serviço documenta a instalação, mas o ambiente compartilhado do monorepo não a trazia por padrão.

Nenhuma violação das regras obrigatórias de modelagem (feature única, alvos separados, horizontes, série univariada, validação temporal sem embaralhamento) foi encontrada no código de treinamento revisado.

## 4. Melhorias necessárias sem ampliar o escopo

Prioridade baixa/média, só após aceite desta análise:

1. Query SPARQL real para agromrv-lite + mapeamento/pivot para o schema canônico (sem frontend nem inferência).
2. Aliases de coluna/granularidade alinhados à ontologia.
3. Documentar política de approved/published quando a fonte for export TTL (ex.: “export só após publicação”).
4. Fonte RDF local opcional (`--ontology-file`) alinhada ao monorepo, sem exigir HTTP.
5. Teste de contrato da query/mapeamento com fixture TTL mínima (não o export completo de ~97k linhas).

**Fora de escopo** (já proibido pelo prompt e pelas rules do módulo): frontend, endpoints de inferência, LSTM como padrão, novas features além de `lactating_cows`.

## Conclusão

O módulo de geração de modelos está coerente com a especificação no caminho CSV e passa nos testes. O principal gap para a próxima etapa é a ponte ontologia real → schema canônico (query, pivot, granularidade, política de publicação), sem ampliar o escopo para UI ou inferência.
