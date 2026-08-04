# 04 — Candidatos a código morto (FASE 1)

**Regra:** nenhum item abaixo está aprovado para remoção automática. Remoção só se classificado DEAD/DUPLICATE sem valor acadêmico, com evidências e registro em `removed-items.md` (FASE 2).

Ferramentas automáticas (grep, AST) usadas apenas como **sinal auxiliar**.

---

## Resumo

| Categoria | Qtd. |
|-----------|------|
| DEAD comprovado | **0** |
| UNCERTAIN (manter) | 8+ |
| DEPRECATED mas ACTIVE | 2+ |
| DUPLICATE estrutural (não necessariamente deletar byte) | 2+ |

---

## Candidatos investigados

### 1. `frontend/scripts/migrate_raw_originals_to_save_file.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN |
| Motivo suspeita | One-shot de migração legada `raw_originals/` |
| Evidências de uso | Nenhuma referência em regressão/CI; docstring própria |
| Evidências de valor | Pode ser necessário para ambientes locais antigos |
| Risco se remover | Médio — quebra migração futura de dados |
| Teste pós-remoção | N/A — **não remover** |
| Confiança | baixa para DEAD |

### 2. `frontend/scripts/migrate_cycles_to_ontology_results.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN |
| Motivo | Regeneração ad hoc de resultados ontológicos |
| Uso | Sem referência em `run_full_regression.py` |
| Risco | Médio (dados históricos) |
| Confiança DEAD | baixa |

### 3. `frontend/scripts/backfill_subcalculations.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN |
| Uso | Fora da regressão |
| Risco | Médio |
| Confiança DEAD | baixa |

### 4. `frontend/scripts/profile_frontend_performance.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN (utilitário dev) |
| Uso | Manual |
| Risco se remover | Baixo funcional; perde ferramenta |
| Ação sugerida | Manter ou mover para `scripts/dev/` documentado |

### 5. `frontend/scripts/report_environment_identity.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN |
| Uso | Manual / diagnóstico data-root |
| Ação | Manter |

### 6. `frontend/scripts/test_provenance_sql_validator.py`

| Campo | Valor |
|-------|-------|
| Classificação | UNCERTAIN / TEST manual |
| Uso | Não orquestrado pela regressão |
| Ação | Manter |

### 7. `schemas/json/anchor_payload.schema.json` (vs `schemas/anchor_payload.schema.json`)

| Campo | Valor |
|-------|-------|
| Classificação | DUPLICATE (possível) |
| Evidência | Teste usa `schemas/anchor_payload.schema.json` |
| Risco | Quebrar consumidores do path `json/` |
| Ação | Diff byte-a-byte na FASE 2; consolidar; **não apagar sem prova** |

### 8. Páginas Dash antigas (`farm.py`, `blockchain.py`, etc.)

| Campo | Valor |
|-------|-------|
| Status | **Já ausentes** — redirects cobrem URLs |
| Classificação | N/A |
| Remoção | Nada a fazer |

---

## Explicitamente NÃO mortos

| Símbolo / arquivo | Por que ACTIVE |
|-------------------|----------------|
| `mock_data.py` | Fallback em todos adapters + validates |
| `SimulatedAnchorProvider` | Default Dash / smoke |
| `EvmAnchorProvider` | Anvil/Sepolia/Forge |
| `process_file_auto` | Ainda exportado (deprecated) |
| `LEGACY_REDIRECTS` | Compatibilidade de URLs |
| `wipe_test_data.py` | Wrapper documentável |
| `generate_audit_reports.py` | Pipeline Cap. 5 |
| `requirements_map.yaml` | Lido pelo gerador (embora divergente) |

---

## Plano para FASE 2 (código)

1. Não remover scripts UNCERTAIN.
2. Documentar deprecated (`process_file_auto`, redirects) em `05` / module docs.
3. Consolidar schema duplicado só após diff + atualização de refs.
4. Lista de remoção efetiva em `08-deletion-plan.md` permanece **quase vazia** (foco em docs stray só se DUPLICATE sem valor — preferir archive).

---

## Critério de confiança para futuras remoções

Para promover UNCERTAIN → DEAD:

1. Grep estático + dinâmico (importlib, strings).
2. Ausência em testes, docs acadêmicos, ADRs, dissertação.
3. Ausência em YAML/JSON/SQL/layouts.
4. Revisão humana.
5. Entrada em `12-removed-items.md` com commit.
