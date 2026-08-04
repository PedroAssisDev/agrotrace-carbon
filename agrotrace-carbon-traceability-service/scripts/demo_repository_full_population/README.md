# Demonstração: população completa do repositório de proveniência

## Objetivo

Esta pasta contém uma **simulação interna** do serviço `agrotrace-carbon-provenance-service`, escrita em Python, que popula o banco **SQLite** com casos fictícios de proveniência **ponta a ponta**.

O foco é demonstrar que todas as tabelas principais dos contextos `pipeline_*`, `prov_core_*`, `semantic_*`, `calculation_*` e `audit_*` podem ser preenchidas de forma **coerente, rastreável e auditável**.

## O que NÃO é

- Não há integração com wrappers reais, ontologia externa, motor de cálculo externo ou blockchain real.
- Não use estes dados em produção; são **fictícios** e prefixados com `demo_repo_`.
- Não utilize `INSERT` SQL manual nas tabelas críticas: a escrita passa por `ProvenanceRecorder`, use cases e repositórios.

## Casos simulados

| Caso | Fazenda | Arquivo | Descrição |
|------|---------|---------|-----------|
| 1 | Fazenda São Pedro | `02_case_annual_direct.py` | Dado anual direto, sem agregação |
| 2 | Fazenda Boa Vista | `03_case_monthly_to_annual.py` | 12 meses → `annual_aggregation` (150 500 L) |
| 3 | Fazenda Santa Clara | `04_case_daily_to_monthly_to_annual.py` | 31 dias (jan) → mensal → 12 meses → anual |
| 4 | Reprocessamento | `05_case_revision_and_reprocessing.py` | Janeiro v1/v2 + `prov_revision` |
| 5 | Auditoria | `06_case_hash_and_blockchain.py` | Hashes complementares e anchors simulados |

## Tabelas preenchidas (33 esperadas)

Ver lista completa em [`demo_tables.py`](demo_tables.py). Nomes reais do schema incluem prefixos duplicados, por exemplo `pipeline_pipeline_run`, `prov_core_prov_entity`, `semantic_semantic_integration_execution`.

## Como executar

Pré-requisito: ambiente instalado (`pip install -e ".[dev]"`).

```bash
# Na raiz do repositório
python scripts/demo_repository_full_population/run_all.py
```

Inicializa o SQLite em `data/provenance.db` (se necessário), executa os casos, valida e imprime o relatório de cobertura.

### Passos individuais

```bash
python scripts/demo_repository_full_population/01_seed_agents_and_methods.py
python scripts/demo_repository_full_population/02_case_annual_direct.py
# ...
python scripts/demo_repository_full_population/validate_full_population.py
python scripts/demo_repository_full_population/table_coverage_report.py
```

### Queries SQL

**Apresentação didática (pipeline completa por caso):**

```bash
sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_01_annual_direct_pipeline.sql
sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_02_monthly_to_annual_pipeline.sql
sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_03_daily_to_monthly_to_annual_pipeline.sql
```

**Linhagem e auditoria (visão geral):**

```bash
sqlite3 data/provenance.db < scripts/demo_repository_full_population/lineage_queries.sql
sqlite3 data/provenance.db < scripts/demo_repository_full_population/audit_queries.sql
```

As queries de **auditoria** devem retornar **zero linhas** quando o banco está consistente.

## Agregação na proveniência

Como o domínio não possui tabelas dedicadas de rollup temporal, a agregação é modelada via:

- Atividade PROV (`prov_core_prov_activity`) com `name` = `annual_aggregation` ou `monthly_aggregation_january`
- Entidade PROV `OTHER` (`annual_aggregate` / agregado mensal)
- Relações `prov_used` (N entradas) e `prov_derived_from` (linhagem)
- Snapshot canônico e cálculo sobre o agregado

## Revisão e reprocessamento

- `pipeline_source_artifact_revision` com `revision_number` 1 e 2
- `prov_core_prov_revision` ligando entidade canônica anterior à nova
- Novo `pipeline_run` filho (`parent_pipeline_run_id`) — append-only, sem sobrescrita

## Hash e blockchain simulado

- `audit_hash_record` em artefatos, lotes, snapshots e resultados
- `audit_blockchain_anchor` com `blockchain_network=demo-chain`, `transaction_hash=demo-tx-...`, `anchor_status=confirmed`
- Metadados `simulated: true`

## Testes automatizados

```bash
pytest tests/integration/demo/test_demo_repository_full_population.py -v
```

## ROTEIRO PARA APRESENTAÇÃO

1. Explicar que o objetivo é demonstrar o banco de proveniência SQLite-first.
2. Executar `table_coverage_report.py` e mostrar tabelas preenchidas.
3. Mostrar `pipeline_pipeline_run` com prefixo `demo_repo_`.
4. Abrir o caso **Fazenda São Pedro** (anual direto).
5. Mostrar que **não** existe atividade `annual_aggregation` nesse run.
6. Abrir o caso **Fazenda Boa Vista** (12 meses).
7. Mostrar `annual_aggregation` com 12 entradas `prov_used`.
8. Abrir o caso **Fazenda Santa Clara** (diário → mensal → anual).
9. Mostrar `monthly_aggregation_january` com 31 entradas.
10. Mostrar `annual_aggregation` com 12 agregados mensais.
11. Mostrar revisão (`source_artifact_revision` + `prov_revision`).
12. Mostrar aprovação humana (`calculation_calculation_review`, `approved`).
13. Mostrar publicação (`calculation_result_publication_execution`).
14. Mostrar `audit_hash_record`.
15. Mostrar `audit_blockchain_anchor` simulado.
16. Executar `audit_queries.sql` — zero problemas.
17. Concluir: todas as tabelas principais preenchidas com dados coerentes.
