# Testes e regressão

## Regressão completa

O runner canônico executa a suíte ponta a ponta em um `AGROTRACE_DATA_ROOT` temporário
(isolado, sem tocar dados operacionais):

```bash
python frontend/scripts/run_full_regression.py
# Publicar evidência versionada:
python frontend/scripts/run_full_regression.py --out docs/audits/current/regressao.json
# Mais rápido:  ... --quick
# Sem Forge:    ... --skip-forge
```

Passos cobertos: testes por serviço (save-file, wrappers, ontology, calculation,
model-training, traceability, blockchain), Forge, testes do frontend, todos os
`validate_*.py`, smoke, ciclo completo e varredura de segredos. **Saída padrão:**
arquivo temporário (não sobrescreve `docs/audits/current/regressao.json`).

## Seed e smoke

| Fluxo | Script | Dados |
|-------|--------|-------|
| Canônico (demo) | `reset_and_seed_pending_cycles.py` | FARM-* + Embrapa P-*/BR-* |
| Alternativo (3 cenários) | `seed_test_scenarios.py` | PROP-ANNUAL/MONTHLY/DAILY-001 |
| Smoke E2E | `run_pipeline_smoke_test.py` | upload → verify |
| Gate blockchain | `test_full_emission_cycle.py` | bloqueio pré-publicação |

Detalhes: [reset-and-seed.md](reset-and-seed.md).

## Testes por serviço

Cada serviço tem sua suíte (pytest, ou unittest no save-file). O runner de regressão os
executa; para rodar isoladamente, use `pytest` no diretório do serviço. Os testes de
blockchain que exigem rede (`blockchain_local`, `sepolia`) são deselecionados por padrão.

## Validadores pontuais

Lista completa: [validation-scripts.md](validation-scripts.md).

## Cenários de avaliação (CE1–CE5)

[../academic/evaluation-scenarios.md](../academic/evaluation-scenarios.md).
