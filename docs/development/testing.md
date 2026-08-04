# Testes e regressão

## Regressão completa

O runner canônico executa a suíte ponta a ponta em um `AGROTRACE_DATA_ROOT` temporário
(isolado, sem tocar dados operacionais):

```bash
python frontend/scripts/run_full_regression.py
```

Passos cobertos: testes por serviço (save-file, wrappers, ontology, calculation,
model-training, traceability, blockchain), Forge, testes do frontend, todos os
`validate_*.py`, smoke, ciclo completo e varredura de segredos. Saída padrão em
`docs/audits/current/regressao.json` (use `--out` para outro destino; `--quick` pula os
e2e longos; `--skip-forge` pula os contratos).

## Cenários oficiais de seed

| ID | Descrição |
|----|-----------|
| `PROP-ANNUAL-001` | Entrada annual direta |
| `PROP-MONTHLY-001` | Monthly (base para consolidação annual) |
| `PROP-DAILY-001` | Daily/intraday quando houver sample; fallback monthly |

Comandos: `seed_test_scenarios.py`, `run_pipeline_smoke_test.py` (ver
[reset-and-seed.md](reset-and-seed.md)).

## Testes por serviço

Cada serviço tem sua suíte (pytest, ou unittest no save-file). O runner de regressão os
executa; para rodar isoladamente, use `pytest` no diretório do serviço. Os testes de
blockchain que exigem rede (`blockchain_local`, `sepolia`) são deselecionados por padrão.

## Cenários de avaliação (CE1–CE5)

Os cenários de avaliação da dissertação estão em
[../academic/evaluation-scenarios.md](../academic/evaluation-scenarios.md).
