# 02 — Classificação de arquivos (FASE 1)

**Legenda de confiança:** alta = referências claras no código/testes/docs; média = inferência forte; baixa = uso não confirmado.

Classificação por **grupos** (arquivo-a-arquivo completo de ~4.900 entradas geradas não é útil). Arquivos UNCERTAIN **não podem ser removidos**.

---

## CANONICAL

| Grupo | Exemplos | Confiança | Nota |
|-------|----------|-----------|------|
| ADRs | `docs/decisions/ADR-00*.md` | alta | Fonte de decisões |
| Arquitetura indexada | `docs/architecture/*.md` | alta | Reescrever alinhando a EVM + 8 rotas |
| Domínio | `docs/domain/*.md` | alta | `yearly` já documentado como alias |
| Auditoria atual | `docs/auditoria-pos-implementacao/09-resultados.json` + MD gerados/alinhados | alta | Fonte RF/RNF/CE no repo |
| Rotas | `frontend/pages/router.py` | alta | 8 rotas + redirects |
| Contratos/ABI | `CarbonEvidenceRegistry.sol`, ABI v1 | alta | |
| Schemas JSON usados em teste | `schemas/anchor_payload.schema.json` (path do teste) | alta | |
| Pipeline orquestração | `local_orchestrator.py`, adapters | alta | |

---

## ACTIVE

| Grupo | Exemplos | Confiança |
|-------|----------|-----------|
| Serviços Python | pacotes `agrotrace-carbon-*` | alta |
| Frontend pages/callbacks/components | `frontend/pages/`, `callbacks/` | alta |
| `mock_data.py` | fallback de import | alta |
| Providers `Simulated` + `Evm` | `providers_registry.py` | alta |
| `validate_*` + `run_full_regression.py` | regressão | alta |
| Seed/smoke/reset scripts | documentados no README | alta |
| Layouts wrappers YAML | registry de layouts | alta |
| Ontologia código | `ontology/schema.py` etc. | alta |
| `generate_audit_reports.py` | lê `requirements_map.yaml` | alta |

---

## GENERATED

| Grupo | Exemplos | Confiança | Ação |
|-------|----------|-----------|------|
| Runtime frontend | `frontend/data/**` | alta | Não versionar; não editar |
| Originais save-file | `save-file/data/originals/**` | alta | Preservar operacionalmente |
| OWL/TTL exports | `ontology_exports/**` | alta | Regeneráveis |
| Model artifacts | `artifacts/**` | alta | |
| Cap. 5 `final/*` auto | gerados por `generate_audit_reports.py` | alta | Arquivar como snapshot |
| Saídas `_gen_reports.py` | MD pos-implementacao (parcialmente) | média | Cabeçalho “gerado” |

---

## TEST

| Grupo | Confiança |
|-------|-----------|
| `*/tests/**`, Forge tests, `frontend/tests/**` | alta |
| Scripts `validate_*` (também ACTIVE operacional) | alta |
| `docs/auditoria-pos-implementacao/tests/` | alta |

---

## ACADEMIC-EVIDENCE

| Grupo | Confiança | Ação FASE 2 |
|-------|-----------|-------------|
| Matrizes / texto-base Cap. 5 | alta | Arquivar |
| `_regressao.json`, `regressao.json`, `09-resultados.json` | alta | Preservar |
| Deployment Sepolia + validação interativa | alta | `docs/evidence/blockchain/` (ponteiros) |
| Plano de figuras Cap. 5 | alta | Arquivar / evidence guide |

**Não apagar.**

---

## HISTORICAL

| Grupo | Confiança | Destino proposto |
|-------|-----------|------------------|
| `docs/auditoria-capitulo-5/*.md` (Aug 3) | alta | `docs/audits/archive/2026-08-03-capitulo-5/` |
| `docs/auditoria-capitulo-5/final/` | alta | mesmo archive, subpasta `final/` |
| `PROMPT-AUDITORIA-CURSOR.md` | alta | `docs/archive/prompts/` |
| `CURSOR_PROMPT.md` (model-training) | média | archive/prompts ou manter no módulo se ainda útil |

---

## LEGACY-COMPATIBILITY

| Item | Evidência | Confiança | Remover? |
|------|-----------|-----------|----------|
| `LEGACY_REDIRECTS` | `router.py` | alta | Não |
| Alias `yearly` → `annual` | domain docs + adapters | alta | Não |
| `TemporalScope.YEARLY` | calculation-service | alta | Não |
| `property_ids` no filtro | `global_filter.py` | alta | Não |
| `process_file_auto` | deprecation + ainda exportado | alta | Não |
| ABI path sem versão | fallback + teste | alta | Não |
| `SimulatedAnchorProvider` | default Dash | alta | Não |
| `wipe_test_data.py` | wrapper reset | alta | Não (compat) |

---

## DUPLICATE

| Par / conjunto | Confiança | Resolução proposta |
|----------------|-----------|-------------------|
| Cap. 5 root vs `final/` vs pos-implementacao | alta | current = pos-impl; resto archive |
| `schemas/anchor_payload.schema.json` vs `schemas/json/` | alta | consolidar num path; manter o do teste |
| `merkle_strategy.md` vs `merkle_tree.md` | média | mesclar ou um canônico + outro archive |
| `anchor_payload.md` vs `anchor_payload_model.md` | média | mesclar apontadores |
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` vs `GUIA_COMPLETO_...` vs docs EVM | média | changelog → archive; guia → development/evidence |
| Docs `docs/audit/*` vs futuros `docs/modules/*` | média | reescrever modules; archive ou merge audit |

---

## DEAD

| Item | Status |
|------|--------|
| — | **Nenhum arquivo autoral com evidência suficiente nesta fase** |

Candidatos investigados mas **não** DEAD: ver `04-dead-code-candidates.md`.

---

## UNCERTAIN

| Item | Motivo | Confiança uso | Remover? |
|------|--------|---------------|----------|
| `migrate_raw_originals_to_save_file.py` | one-shot; sem refs CI | baixa | Não |
| `migrate_cycles_to_ontology_results.py` | manutenção ad hoc | baixa | Não |
| `backfill_subcalculations.py` | fora da regressão | baixa | Não |
| `profile_frontend_performance.py` | utilitário manual | baixa | Não |
| `report_environment_identity.py` | utilitário manual | baixa | Não |
| `test_provenance_sql_validator.py` | fora da regressão | baixa | Não |
| `schemas/json/anchor_payload.schema.json` | possível cópia | média | Não até diff |
| Docs ausentes citados | `conceptual_model_mrv.md`, `filter_architecture_mrv.md` | — | N/A (já ausentes) |

---

## Resumo quantitativo por classe (grupos, não bytes)

| Classe | Grupos principais |
|--------|-------------------|
| CANONICAL | ~15 |
| ACTIVE | módulos + frontend + scripts validate |
| GENERATED | 6+ árvores grandes |
| TEST | todas as suítes |
| ACADEMIC-EVIDENCE | Cap. 5 + Sepolia |
| HISTORICAL | auditoria Cap. 5 completa |
| LEGACY-COMPATIBILITY | ~8 mecanismos |
| DUPLICATE | ~6 conjuntos |
| DEAD | 0 |
| UNCERTAIN | ~8 scripts/artefatos |

Detalhamento Markdown: `03-markdown-audit.md`.
