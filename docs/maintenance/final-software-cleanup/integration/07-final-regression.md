# 07 — Regressão final

## Baseline (pré-refatoração)

- Arquivo: `_regressao-baseline.json`
- pass=39 fail=2 (`validate_emulated_import`, `validate_preliminary_calculation_fix`)

## Pós-legado (modo `--quick`)

- Arquivo: `_regressao-final-quick.json`
- pass=38 fail=0
- Inclui suítes dos 8 projetos, Forge, frontend tests, todos `validate_*`, `scan_secrets`
- Omite `run_pipeline_smoke_test` e `test_full_emission_cycle` (flag `--quick`)

## Legado

- `scripts/verify_no_active_legacy.py` → `legacy_active_count = 0`
