# Reset e seed

```bash
cd frontend
python scripts/reset_test_environment.py --confirm
python scripts/seed_test_scenarios.py --wipe-first
python scripts/run_pipeline_smoke_test.py
```

Reset remove ciclos, artefatos gerados e DBs locais; recria a estrutura.

Seed cria três propriedades oficiais (annual / monthly / daily-consolidável) até pendência de aprovação.
