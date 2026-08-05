# Reset e seed

Operações **destrutivas** sobre `$AGROTRACE_DATA_ROOT`. Exigem `--confirm`.

## Fluxo canônico (demo: simulados + Embrapa)

```bash
cd frontend

# Wipe → simulados (FARM-*) → Embrapa monthly (P-*) + annual (BR-*)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo

# Só simulados
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --skip-embrapa

# Ano dos inventários anuais Embrapa (default: 2022)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --embrapa-year 2022
```

| Flag | Função |
|------|--------|
| `--confirm` | Obrigatório |
| `--seed` | Semente RNG dos CSVs simulados (default `42`) |
| `--profile demo\|full` | `demo` = conjunto padrão; `full` = perfis extras |
| `--skip-embrapa` | Não importa Embrapa |
| `--embrapa-year` | Ano dos anuais BR-* |

Status esperado após o seed: ciclos pendentes de aprovação (blockchain ainda bloqueado).

## Aprovação em massa

```bash
cd frontend
python scripts/approve_all_pending_cycles.py --dry-run
python scripts/approve_all_pending_cycles.py --confirm
python scripts/approve_all_pending_cycles.py --confirm --property-prefix FARM-
```

Avança: revisão → aprovação → publicação → evidências → ancoragem → verificação.

## Fluxo alternativo (3 cenários PROP-*)

Mantido para testes pontuais alinhados a CE oficiais antigos; **não** é o seed de demo
do README raiz.

```bash
cd frontend
python scripts/reset_test_environment.py --confirm
python scripts/seed_test_scenarios.py --wipe-first
python scripts/run_pipeline_smoke_test.py
```

Cria três propriedades (`PROP-ANNUAL-001`, `PROP-MONTHLY-001`, `PROP-DAILY-001`) até
pendência de aprovação.

## Smoke após seed

```bash
python scripts/run_pipeline_smoke_test.py
```
