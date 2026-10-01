# Frontend AgroTrace Carbon

Interface Dash + orquestração in-process da pipeline MRV.

## Entrypoint

```bash
python main.py
# UI: http://127.0.0.1:8050
```

Não use `app.py` (conflito com o pacote `app` do blockchain-service).

## Rotas (8)

| Rota | Label |
|------|-------|
| `/` | Painel Executivo |
| `/data-entry` | Entrada de Dados |
| `/calculations` | Cálculos de Emissão |
| `/approval` | Revisão e Aprovação |
| `/indicators` | Análise Geral |
| `/previsoes` | Previsões |
| `/technical-audit` | Auditoria Técnica (9 abas) |
| `/settings` | Configurações |

Paths desconhecidos caem no dashboard. Não há `LEGACY_REDIRECTS`. Blockchain/evidências:
aba em `/technical-audit`.

### Previsões (`/previsoes`)

| Aba | Função |
|-----|--------|
| Modelos | Disponibilidade, criar ausentes, atualizar stale, retreinar, personalizado |
| Cenário por rebanho | Inferência de regressão global (`lactating_cows`) |
| Projeção histórica | Série temporal mensal da propriedade (horizonte 3) |

- Propriedade = `farm_id` do filtro global (sem “Todas”).
- Inferência: `services/forecast_inference/`
- Treinamento: `services/model_training_adapter.py` → `ModelTrainingFacade`
- Artefatos: `MODEL_TRAINING_ARTIFACTS_DIR` / `MODEL_REGISTRY_PATH` / `MODEL_TRAINING_CONFIG_PATH`

## Scripts oficiais

```bash
# Seed canônico (demo): wipe → FARM-* → Embrapa P-* / BR-*
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo

# Aprovar em massa (publicação → evidências → blockchain)
python scripts/approve_all_pending_cycles.py --dry-run
python scripts/approve_all_pending_cycles.py --confirm

# Smoke e gate
python scripts/run_pipeline_smoke_test.py
python scripts/test_full_emission_cycle.py
python scripts/run_full_regression.py
```

Fluxo alternativo (3 cenários `PROP-*`): `reset_test_environment.py` +
`seed_test_scenarios.py` — ver [docs/development/reset-and-seed.md](../docs/development/reset-and-seed.md).

Documentação do monorepo: [../docs/README.md](../docs/README.md)
