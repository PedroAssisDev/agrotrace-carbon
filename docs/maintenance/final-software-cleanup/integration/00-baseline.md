# 00 — Baseline (FASE 0)

**Data:** 2026-08-04  
**Branch:** `refactor/final-software-cleanup`  
**HEAD (início):** `77641586eb6b0eff9d1d050da40476436af088f7`  
**Base anterior:** `chore/project-organization`  
**Python:** 3.13.5  
**Topologia Git:** monorepo (1× `.git` raiz; Foundry `forge-std` com `.git` aninhado esperado)

## Confirmações operacionais

- Working tree limpa no checkout da branch de trabalho.
- Sem push.
- Sem transações Sepolia / rede externa.
- Testes sob `AGROTRACE_DATA_ROOT` temporário (runner de regressão).
- Bancos/ciclos/ontologias/evidências operacionais não alterados deliberadamente nesta fase.

## Varredura de segredos

- Nenhum `.env` tracked (exceto exemplos).
- Hits de padrões `PRIVATE_KEY` / RPC em código e testes de unidade — referências a variáveis/config, não credenciais commitadas.
- Status: **PASS** (sem segredo operacional no Git).

## Inventário operacional (somente leitura)

| Artefato | SHA-256 | Tamanho |
|----------|---------|---------|
| `frontend/data/db/provenance.db` | `42BAFB2FBB071C04659B2224B13C5727D05665B11233F10D51F4100CA0C572AF` | 26341376 |
| `frontend/data/db/blockchain_service.db` | `C0B9CAFF1E0F1164C50C7F1E07E160CCE3430E76E2188D7FB7E713CB861A2645` | 172032 |
| `agrotrace-carbon-blockchain-service/blockchain_service.db` | ausente | — |

## Regressão

Saída JSON: `_regressao-baseline.json` (mesmo diretório).

| Métrica | Valor |
|---------|-------|
| pass_count | 39 |
| fail_count | 2 |
| duração | ~1371 s |
| Python | 3.13.5 |

### Falhas da baseline

1. **`validate_emulated_import`** — `isolated_data_root` reutilizava `--data-root` compartilhado da regressão (poluição de ciclos).  
2. **`validate_preliminary_calculation_fix`** — script one-shot legado ainda no glob `validate_*.py` (falhava sem `factor_catalog`); o canônico `validate_preliminary_calculation_form` passou.

### Estado P1–P3 na baseline

- **P1** (`by_gas`): PASS na regressão (`validate_emission_calculation_details`).
- **P2** (`factor_catalog`): caminho canônico PASS; falha vinha do script `_fix`.
- **P3** (`Lot`): classe `Lot` + `belongsToLot` / `belongsToProperty` já presentes em `ontology/schema.py`.

## Correções aplicadas na FASE 1 (pós-baseline)

- `isolated_data_root` ignora `--data-root` compartilhado por padrão.
- `validate_preliminary_calculation_form` isolado + `onto_cache.clear()`.
- `validate_preliminary_calculation_fix.py` movido para `academic-evidence/one-shot-scripts/`.

## Projetos identificados

1. agrotrace-carbon-save-file  
2. agrotrace-carbon-wrappers-service  
3. agrotrace-carbon-ontology-manager  
4. agrotrace-carbon-calculation-service  
5. agrotrace-carbon-model-training-service  
6. agrotrace-carbon-traceability-service  
7. agrotrace-carbon-blockchain-service  
8. frontend  
