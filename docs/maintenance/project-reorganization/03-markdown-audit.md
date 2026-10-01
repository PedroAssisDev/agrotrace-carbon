# 03 — Auditoria Markdown (FASE 1)

**Total aproximado:** ~108 `.md` autorais (excl. caches).  
**Ações possíveis:** manter e reescrever | manter sem alteração | mover | arquivar | mesclar | gerar automaticamente | remover | incerto.

Critérios verificados: atualidade vs código (8 rotas / 9 abas), menções a 12 telas, YEARLY como canônico, blockchain só simulada, Sepolia, links quebrados, requisitos.

---

## Raiz

| Arquivo | Ação | Motivo |
|---------|------|--------|
| `README.md` | manter e reescrever | Curto; corrige “só simulada”; 8 rotas; link docs; nome acadêmico MRV |
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` | mover → archive/evidence | Changelog Jul 31; não é README |

---

## `docs/` — índice e arquitetura

| Arquivo | Ação | Notas |
|---------|------|-------|
| `docs/README.md` | manter e reescrever | Índice por público; status; sem listar archive como atual |
| `architecture/overview.md` | manter e reescrever | Boundaries; terceiro ciclo; EVM |
| `architecture/pipeline.md` | mesclar → `data-lifecycle.md` | Ainda diz “ancoragem simulada” |
| `architecture/components.md` | mesclar → `component-responsibilities.md` | |
| `architecture/storage-and-artifacts.md` | manter e reescrever | Incluir `AGROTRACE_DATA_ROOT` |
| `architecture/append-only-tables.md` | manter / apontar de security | Pode ficar sob architecture |

---

## `docs/domain/`

| Arquivo | Ação |
|---------|------|
| `temporal-and-organizational-granularity.md` | manter (já correto sobre yearly) → apontar de modules |
| `calculations.md` | mesclar conteúdo em `modules/calculation-service.md` |
| `statuses-and-events.md` | mesclar → `result-state-model.md` |

---

## `docs/operations/`

| Arquivo | Ação |
|---------|------|
| `running-the-prototype.md` | manter e reescrever → `development/setup.md` | **7 rotas** (falta `/previsoes`) |
| `configuration.md` | mover → `development/configuration.md` |
| `reset-and-seed.md` | mover → `development/` |

---

## `docs/audit/` (estável, não é Cap. 5)

| Arquivo | Ação | Nota |
|---------|------|------|
| `provenance.md` | mesclar → modules/traceability + architecture | |
| `approval-and-publication.md` | mesclar → lifecycle / frontend | |
| `evidence-and-blockchain.md` | manter e reescrever | Afirma MVP só simulado — **desatualizado** |

---

## `docs/testing/`

| Arquivo | Ação |
|---------|------|
| `test-scenarios.md` | mover → `development/testing.md` ou `academic/evaluation-scenarios.md` (cenários PROP-*) |

---

## `docs/decisions/` (ADRs)

| Arquivo | Ação |
|---------|------|
| ADR-001, ADR-002, ADR-003 | mover → `docs/architecture/decisions/` | manter sem alteração de conteúdo decisório; atualizar links |

---

## `docs/auditoria-pos-implementacao/` — AUDITORIA ATUAL

| Arquivo | Ação |
|---------|------|
| `00`–`10` MD + `09-resultados.json` + `_regressao.json` | mover → `docs/audits/current/` |
| `_gen_reports.py` + `tests/` | mover junto (ferramenta da auditoria atual) |
| Conteúdo | **não reescrever resultados históricos** |

---

## `docs/auditoria-capitulo-5/` — HISTÓRICO

| Arquivo | Ação |
|---------|------|
| `PROMPT-AUDITORIA-CURSOR.md` | arquivar → `docs/archive/prompts/` |
| `relatorio-completo.md`, `matriz-*`, `pendencias`, `comandos-*`, `plano-evidencias`, `texto-base-*` | arquivar → `audits/archive/2026-08-03-capitulo-5/` |
| `final/*` | arquivar (snapshot gerado) |
| `requirements_map.yaml` | arquivar → `archive/superseded-requirements/` + atualizar gerador | **ainda ACTIVE via script** |

---

## Frontend

| Arquivo | Ação |
|---------|------|
| `frontend/README.md` | manter e reescrever pontualmente | Já lista 8 rotas — alinhado |

---

## Blockchain-service

| Arquivo | Ação |
|---------|------|
| `README.md` | manter; apontar para `docs/modules/blockchain-service.md` |
| `GUIA_COMPLETO_ETHEREUM_SEPOLIA.md` | mover → development ou evidence | operacional longo |
| `docs/architecture.md` | mesclar / apontar canônico monorepo |
| `docs/ethereum_integration.md`, `sepolia_deployment.md`, `anvil_*`, `validacao_interativa_sepolia.md` | manter como docs de módulo ou mover trechos operacionais |
| `docs/security_and_secrets.md` | alimentar `architecture/security-and-integrity.md` |
| `hash_strategy`, `merkle_*`, `anchor_payload*` | mesclar duplicatas; um canônico |
| `evidence_package_model`, `sqlite_schema`, etc. | manter referenciados pelo module doc |
| `contracts/README.md` | manter |
| `schemas/canonical/canonicalization_rules.md` | CANONICAL técnico |

---

## Wrappers-service (~25 docs)

| Ação | Nota |
|------|------|
| Criar `docs/modules/wrappers-service.md` canônico | |
| Manter `docs/layouts/*.md` e contratos técnicos no serviço | ACTIVE |
| `docs/README.md` do serviço | virar índice local apontando monorepo |
| Vários overlaps (architecture, processing-flow, api-guide) | mesclar ou marcar como detalhe de implementação |

---

## Traceability-service

| Arquivo | Ação |
|---------|------|
| `README.md`, `ARCHITECTURE.md`, `RUNBOOK.md`, `API_EXAMPLES.md` | mesclar → module doc + archive extras se duplicados |
| `docs/provenance_service_complete_explanation.md` | manter ou arquivar se superado pelo module |
| `docs/blockchain_observability_preparation.md` | ACTIVE / acadêmico |
| `scripts/.../README.md` | TEST/demo — manter |

---

## Model-training

| Arquivo | Ação |
|---------|------|
| `README.md` | manter + link module |
| `PROJECT_SPEC.md`, `ANALYSIS_REPORT.md`, `VALIDATION_REPORT.md` | arquivar ou academic/evidence |
| `CURSOR_PROMPT.md` | arquivar → `archive/prompts/` |

---

## Calculation / Ontology / Save-file

| Arquivo | Ação |
|---------|------|
| `calculation-service/README.md` | manter mínimo + module canônico |
| `REVISAO_TECNICA_CALCULOS.md` | arquivar ou academic |
| `ontology-manager/README.md` + `docs/ontology_agromrv_lite.md` | module + detalhe |
| `save-file/README.md` | module |

---

## Problemas transversais detectados

| Problema | Onde | Correção FASE 2 |
|----------|------|-----------------|
| “12 telas” | rules Cursor, Cap. 5 histórico | rules + docs atuais → 8 rotas + 9 abas |
| Só “ancoragem simulada” | README, pipeline, evidence-and-blockchain | Documentar default simulado **e** EVM |
| 7 rotas | `running-the-prototype.md` | Incluir `/previsoes` |
| Links para `conceptual_model_mrv.md` / `filter_architecture_mrv.md` | rules / matrizes | Remover ou recriar sob academic |
| PDF dissertação | citados, ausente | Não inventar; usar JSON alinhado |
| YEARLY como valor de UI | não nos docs canônicos de domínio | OK — manter como alias |
| Sepolia “executada” em auditoria | pos-impl declara **não** reexecutada | Preservar limitação nos docs atuais |

---

## Contagem por ação (aprox.)

| Ação | Qtd. aprox. |
|------|-------------|
| manter e reescrever | ~15 |
| manter sem alteração (ADRs, layouts técnicos) | ~20 |
| mover | ~25 |
| arquivar | ~25 |
| mesclar | ~20 |
| gerar automaticamente | requirements.md, partes de audits |
| remover | **0** nesta fase |
| incerto | ~5 |

Nenhum Markdown acadêmico ou de auditoria classificado para **remoção**.
