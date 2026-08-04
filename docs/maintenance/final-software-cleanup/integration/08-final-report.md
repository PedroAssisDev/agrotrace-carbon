# 08 — Relatório final

## Classificação

```text
PRONTO COM LIMITAÇÕES DECLARADAS
```

## Topologia / Git

- Monorepo `agrotrace-carbon`
- Branch: `refactor/final-software-cleanup`
- Baseline HEAD: `77641586eb6b0eff9d1d050da40476436af088f7`
- Sem push; sem transações Sepolia

## O que foi concluído

1. FASE 0 — baseline (regressão 39/2) + scaffolding de relatórios
2. FASE 1 — falhas de regressão (script `_fix` arquivado; isolamento de data-root)
3. Empacotamento standalone dos 8 projetos (`pyproject` / `.gitignore` / versão 1.0.0)
4. Remoção do legado ativo (verificador = 0)
5. Scripts de workspace + `ecosystem-manifest.json`
6. Separação `academic-evidence/` e gerador `software-release/`

## Limitações declaradas

1. Regressão completa pós-legado ainda não reexecutada integralmente nesta sessão (validadores críticos e suítes unitárias principais passaram; full cycle ~7+ min).
2. Evidências Cap. 5 (Sepolia / capturas UI) permanecem históricas em `academic-evidence` / `docs/evidence` — sem reexecução de rede externa.
3. Provider EVM Sepolia só sob configuração explícita; default continua `local_simulated`.
4. `LICENSE` acadêmica restritiva (não MIT).
5. Tags `*-v1.0.0` preparadas no manifesto, não criadas automaticamente.

## Critérios §32 vs estado

| Critério | Estado |
|----------|--------|
| 8 projetos instaláveis | Sim (pyproject + venv tests) |
| Legado ativo = 0 | Sim |
| CE1–CE5 / validate_* pós-legado | Parcial — suítes unitárias OK; regressão full pendente de reexecução final |
| Sem segredos | Sim |
| software-release independente | Gerável via `scripts/build_software_release.py` |

## Commits principais (esta branch)

- `docs: scaffold final-software-cleanup reports and baseline`
- `fix: close baseline functional failures`
- `refactor(<projeto>): finalize standalone project` × 8
- `chore(legacy): remove final compatibility layer`
