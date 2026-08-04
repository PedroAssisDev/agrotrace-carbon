# 11 — Migração executada (FASE 2)

Branch: `chore/project-organization`. Baseline: `c724282`.

## Commits

| Commit | Escopo |
|--------|--------|
| `c724282` | Baseline (relatórios FASE 1 + normalização de fim de linha) |
| `b900141` | Moves: auditorias, ADRs, evidências, prompts + atualização de referências |
| `b8b12ff` | Arquitetura reescrita (8 rotas, provider EVM) |
| `4ffb11b` | `development/` consolidado |
| `cec4a35` | `academic/` + `validate_requirements_ids.py` |
| `897347b` | `modules/` + README raiz + índice |
| `c10216c` | Verificador de links Markdown + correções pré-existentes |
| `56970ff` | Ponteiros dos READMEs de serviço |
| `71ca742` | Relatórios finais 11–18 + `regressao.json` |

## Ordem seguida

Passos 0–8 do [07-migration-plan.md](07-migration-plan.md): baseline e varredura de
segredos; estrutura `docs/`; movimentação de auditorias/ADRs; requisitos e validação de
IDs; arquitetura; módulos/development/academic; README/índice; links. Passo 9–10
(remoções) sem itens. Passo 11 (regressão: 39 PASS / 2 FAIL pré-existentes) e
Passo 12 (relatórios 11–18) concluídos.

## Segurança

- Sem `reset`/limpeza de dados; sem transações externas; `AGROTRACE_DATA_ROOT` temporário na regressão.
- `git mv` para preservar histórico; nenhum arquivo de dado operacional tocado.
- Varredura de segredos: 0 achados no baseline.
