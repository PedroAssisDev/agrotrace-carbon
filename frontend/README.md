# Frontend AgroTrace Carbon

Interface Dash + orquestração in-process da pipeline MRV.

## Entrypoint

```bash
python main.py
```

## Rotas

`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`, `/technical-audit`, `/settings`

### Previsões (`/previsoes`)

Três abas:

| Aba | Função |
|-----|--------|
| Modelos | Disponibilidade, criar ausentes, atualizar stale, retreinar, personalizado |
| Cenário por rebanho | Inferência de regressão global (`lactating_cows`) |
| Projeção histórica | Série temporal mensal da propriedade (horizonte 3) |

- Propriedade = `farm_id` do filtro global (sem “Todas”).
- Inferência: `services/forecast_inference/`
- Treinamento: somente via `services/model_training_adapter.py` → `ModelTrainingFacade` (sem sklearn no frontend).
- Artefatos: `MODEL_TRAINING_ARTIFACTS_DIR` / `MODEL_REGISTRY_PATH` / `MODEL_TRAINING_CONFIG_PATH`.

## Scripts oficiais

```bash
python scripts/reset_test_environment.py --confirm
python scripts/seed_test_scenarios.py --wipe-first
python scripts/run_pipeline_smoke_test.py

# Reset + simulados (FARM-*) + Embrapa monthly (P-*) + annual (BR-*, year=2022)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42

# Aprovar em massa ciclos pendentes (publicacao -> evidencias -> blockchain)
python scripts/approve_all_pending_cycles.py --dry-run
python scripts/approve_all_pending_cycles.py --confirm
python scripts/approve_all_pending_cycles.py --confirm --property-prefix FARM-
```

Documentação do monorepo: [../docs/README.md](../docs/README.md)
