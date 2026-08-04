# 16 — Testes e regressão (FASE 2)

**Data:** 2026-08-04  
**Ambiente:** `AGROTRACE_DATA_ROOT` temporário (isolado; sem tocar dados operacionais).  
**Comando:** `python frontend/scripts/run_full_regression.py --out docs/audits/current/regressao.json`  
**Relatório JSON:** [docs/audits/current/regressao.json](../../audits/current/regressao.json)

## Resultado agregado

| Métrica | Valor |
|---------|-------|
| Pass | 39 |
| Fail | 2 |
| Transações externas | nenhuma |
| Forge | build + test OK |
| scan_secrets | 0 findings |

## Suítes por serviço

| Suíte | Resultado |
|-------|-----------|
| save-file (unittest) | PASS |
| wrappers (pytest) | PASS |
| ontology-manager (pytest) | PASS |
| calculation-service (pytest) | PASS |
| model-training-service (pytest) | PASS |
| traceability-service (pytest) | PASS |
| blockchain-service (pytest, sem sepolia/local live) | PASS |
| forge build | PASS |
| forge test | PASS |
| frontend/tests | PASS |

## Scripts validate_* e E2E

Todos os `validate_*.py` foram executados, além de:

| Script | Resultado |
|--------|-----------|
| `run_pipeline_smoke_test.py` | PASS |
| `test_full_emission_cycle.py` | PASS |
| `validate_requirements_ids.py` | PASS |
| `check_markdown_links.py` (separado) | PASS após criação deste arquivo |
| `scan_secrets.py` | PASS |

## Falhas (pré-existentes / não introduzidas pela reorganização)

| Script | Exit | Nota |
|--------|------|------|
| `validate_emulated_import` | 1 | Falha em `count_pending_approval` / status awaiting após import emulado. Não depende de paths documentais movidos. |
| `validate_preliminary_calculation_form` | 1 | `RuntimeError`: parâmetros obrigatórios ausentes na ontologia (`factor_catalog`). Lacuna funcional já conhecida na auditoria (defaults pending). |

Estas falhas **não** são regressões da FASE 2 (movimentação/reescrita documental). A reorganização não alterou adapters de cálculo nem o fluxo de import emulado.

## Compatibilidade legada verificada indiretamente

- Alias `yearly` / domínio temporal: cobertos por `validate_temporal_model` (PASS) e testes de ontology/calculation.
- Redirects legados: cobertos por estrutura de rotas + `validate_technical_audit` / frontend tests (PASS).
- Provider simulado (default Dash): smoke + full emission cycle (PASS) sem rede externa.
- Gate blockchain pós-publicação: `test_full_emission_cycle` (PASS).

## Critério de aprovação da FASE 2 (validação)

1. Regressão não introduziu falhas novas além das falhas funcionais pré-existentes documentadas — **atendido**.
2. Links dos docs atuais válidos — **atendido** (`broken_count=0` após este relatório).
3. Nenhuma evidência acadêmica perdida — **atendido** (apenas `git mv` + archive).
4. Compat legada exercitada indiretamente — **atendido**.
5. Deletion plan respeitado (vazio) — **atendido**.
6. Git permite reverter — **atendido** (branch `chore/project-organization`).
