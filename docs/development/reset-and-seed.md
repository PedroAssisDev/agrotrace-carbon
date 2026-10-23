# Reset e seed

Operações **destrutivas** sobre `$AGROTRACE_DATA_ROOT`. Exigem `--confirm`.

## Dois grupos da avaliação

1. **Simulados (`FARM-*`)** — RNG com `--seed 42` (perfil `demo`: 17 ciclos).
2. **Embrapa** — mensal `P-*` e anual `BR-*`. O seed executa
   `agrotrace-carbon-save-file/data/embrapa/split.py` automaticamente antes da
   importação. Se as pastas geradas ficarem vazias, a importação **falha
   explicitamente** (não retorna 0 ciclos em silêncio).

O grupo **diário** está fora do escopo da avaliação. Fixtures diárias em
`validate_temporal_model.py` / `validate_emulated_import.py` exercitam
*capacidade* da arquitetura (layout `intraday:v1`), não o seed canônico.

## Fluxo canônico (demo: simulados + Embrapa)

```bash
cd frontend

# Wipe → simulados (FARM-*) → split Embrapa → monthly (P-*) + annual (BR-*)
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

Contagens de referência após seed completo: **17** simulados + **386** mensais
Embrapa + **50** anuais Embrapa = **453** ciclos.

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
do README raiz. Inclui `PROP-DAILY-001` como capacidade, não como grupo da avaliação.

```bash
cd frontend
python scripts/reset_test_environment.py --confirm
python scripts/seed_test_scenarios.py --wipe-first
python scripts/run_pipeline_smoke_test.py
```

## Smoke após seed

```bash
python scripts/run_pipeline_smoke_test.py
```
