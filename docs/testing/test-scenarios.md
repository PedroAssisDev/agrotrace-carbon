# Cenários oficiais de teste

| ID | Descrição |
|----|-----------|
| `PROP-ANNUAL-001` | Entrada annual direta |
| `PROP-MONTHLY-001` | Monthly (base para consolidação annual) |
| `PROP-DAILY-001` | Daily/intraday quando houver sample; fallback monthly |

Comandos: `seed_test_scenarios.py`, `run_pipeline_smoke_test.py`.

Validações adicionais legadas em `frontend/scripts/validate_*.py` podem ser usadas pontualmente; o smoke oficial é a referência.
