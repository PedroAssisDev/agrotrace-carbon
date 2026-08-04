# Tabelas append-only (ledger de proveniência e auditoria)

**Importante:** nem todo o banco é append-only. Apenas tabelas classificadas como *ledger*
têm UPDATE/DELETE bloqueados. Tabelas operacionais, outbox e catálogos permanecem mutáveis.

Enforcement em duas camadas:

1. **Aplicação** — repositórios de ledger expõem apenas `add`/`get` (sem `update`/`delete`);
   correções geram novo evento, revisão ou entidade derivada.
2. **SQLite** — triggers `CREATE TRIGGER IF NOT EXISTS` que abortam UPDATE/DELETE
   (`install_sqlite_append_only` / equivalente blockchain).

Fontes canônicas:

- Provenance: `agrotrace-carbon-traceability-service/.../sqlite_append_only.py`
- Blockchain: `agrotrace-carbon-blockchain-service/.../sqlite_append_only.py`

Instalação idempotente no bootstrap do frontend (`init_provenance_db` / `init_blockchain_db`).
Não executar migração destrutiva no banco operacional; triggers faltantes são instalados
com `IF NOT EXISTS` em bancos novos e existentes.

---

## Provenance DB (`provenance.db`)

### Ledger / eventos imutáveis (UPDATE/DELETE bloqueados; INSERT ok)

| Tabela | Notas |
|--------|-------|
| `prov_core_prov_bundle` | Bundle PROV; `close()` na API lança erro explícito (imutável) |
| `prov_core_prov_entity` | Exceção controlada: só `invalidated_at` (soft-invalidate) |
| `prov_core_prov_activity` | Atividades PROV |
| `prov_core_prov_agent` | Agentes PROV |
| `prov_core_prov_used` | Relação used |
| `prov_core_prov_generated` | Relação generated |
| `prov_core_prov_derived_from` | Relação derived |
| `prov_core_prov_associated_with` | Associação |
| `prov_core_prov_revision` | Revisão (correção = nova linha) |
| `prov_core_prov_attribute` | Atributos |
| `pipeline_source_artifact` | Artefato de intake |
| `pipeline_source_artifact_revision` | Revisão de artefato |
| `pipeline_wrapper_execution` | Execução de wrapper |
| `pipeline_normalized_batch` | Lote normalizado |
| `semantic_semantic_integration_execution` | Execução semântica |
| `semantic_canonical_snapshot` | Snapshot canônico |
| `semantic_canonical_snapshot_item` | Itens do snapshot |
| `semantic_ontology_resource_link` | Link ontológico |
| `calculation_calculation_execution` | Execução de cálculo |
| `calculation_calculation_parameter_value` | Valores de parâmetro |
| `calculation_calculation_result_item` | Itens de resultado |
| `calculation_calculation_review` | Evento de revisão |
| `calculation_result_aggregation_link` | Aresta de agregação |
| `audit_hash_record` | Registro de hash |
| `audit_audit_event` | Evento de auditoria |

### Operacionais mutáveis

| Tabela | Motivo |
|--------|--------|
| `pipeline_pipeline_run` | Status do run |
| `pipeline_wrapper_definition` | Catálogo (`deactivate`) |
| `calculation_calculation_method` | Catálogo de métodos |
| `calculation_calculation_method_version` | Versões de método |
| `calculation_calculation_parameter_set` | Conjunto de parâmetros |
| `calculation_calculation_result_set` | Status / supersede / approved / published |
| `calculation_result_publication_execution` | Execução de publicação |
| `audit_blockchain_anchor` | Espelho de ciclo de âncora |
| `reporting_period` | Registro de períodos |

### Outbox (update de estado permitido)

| Tabela | Motivo |
|--------|--------|
| `audit_outbox_event` | `mark_published` / `mark_failed` |

### Projeções / read models

Nenhuma tabela SQLite dedicada. A UI reconstrói agregações em Python
(`frontend/services/*_view_service.py`) e no JSON do ciclo (`frontend/data/cycles/`).

---

## Blockchain DB (`blockchain_service.db`)

### Ledger imutável (triggers UPDATE/DELETE)

| Tabela | Notas |
|--------|-------|
| `hash_record` | Hashes de evidência |
| `verification_log` | Eventos de verificação |
| `audit_log` | Trilha de auditoria operacional do serviço |

### Operacionais mutáveis

| Tabela | Motivo |
|--------|--------|
| `anchor_request` | Máquina de status |
| `evidence_package` | Status / hashes do pacote |
| `evidence_item` | Port ainda permite `update` (exceção documentada; não há trigger) |
| `blockchain_transaction` | Status / receipt |
| `blockchain_network` | Catálogo de redes |
| `observer_state` | Watermark do consumidor de outbox |
| `anchoring_attempt` | Ciclo de tentativas |

### Outbox local

Nenhum. O serviço consome `audit_outbox_event` da proveniência.

---

## O que a política não impede

- Marcar outbox como processada/falha
- Atualizar status de `pipeline_run`, result sets e âncoras espelho
- Reconstruir read models na UI
- Migração/schema controlada em banco **temporário** de teste
- Soft-invalidate de `prov_entity` (`invalidated_at` apenas)
