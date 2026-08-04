# Comparação antes/depois — regressão final

Gerada automaticamente a partir da execução em `regressao.json`.

## Antes (audit Cap. 5 de 2026-08-03 — pendências conhecidas)

| Problema | Status anterior |
|----------|-----------------|
| `jsonschema` ausente → schema test não coletado | P-M03 |
| `validate_pending_approval_seed` exige contagem 17 no ambiente operacional | P-M02 |
| `validate_property_filter` sensível a label Embrapa | P-M02 |
| `validate_temporal_model` Jan–Jun inconsistente / daily ausente | P-M02 |
| Fallback compact JSON em `hash_helpers.sha256_dict` | P-B02 |
| Sem teste negativo de predição na ontologia final | P-B03 |
| `scan_secrets` 415 falsos positivos (hashes SHA-256) | RNF012 |
| Canonicalização duplicada / rótulo colidente no traceability | RF018 |

## Depois (esta regressão)

| Item | Resultado |
|------|-----------|
| `jsonschema` via `pip install -e ".[dev]"` | 6 testes de schema coletados; blockchain pytest PASS |
| `validate_pending_approval_seed` | Fixture isolado; não assume 17 global — PASS |
| `validate_property_filter` | IDs canônicos + label separado — PASS |
| `validate_temporal_model` | daily/monthly/annual + Jan–Jun=6 — PASS |
| Canonicalização única `json_canonical_v1` + registry versionado | PASS (vetores + parity) |
| Fallback compacto removido (fail-closed) | PASS |
| Traceability emite `prov_canonical_v1` | 115 passed |
| `validate_prediction_separation` | PASS (guarda + inventário) |
| `scan_secrets` contextual | findings_count=0 — PASS |
| Smoke + full emission cycle | PASS |
| Forge build/test | PASS |

## Contagens da matriz (grupos separados)

| Grupo | A | P | N | NV |
|-------|---|---|---|----|
| RF | 17 | 4 | 0 | 0 |
| RNF | 12 | 0 | 0 | 0 |
| RN | 10 | 0 | 0 | 0 |
| CE | 4 | 1 | 0 | 0 |

## Falhas funcionais remanescentes (declaradas)

1. **validate_emission_calculation_details** — asserção `série por gás` (exit 1). Não mascarada.
2. **validate_preliminary_calculation_fix** — `factor_catalog` ausente no fixture do script (exit 1). Não mascarada.

## Identificação Git

- Branch `master` sem commits no início da sessão (`fatal: Needed a single revision`).
- Relatórios identificados por inventário + timestamp UTC em `regressao.json`.
- `forge` e suítes Python executados sob `AGROTRACE_DATA_ROOT` temporário (bancos operacionais fora do escopo).
- Nenhuma transação Sepolia nova; segredos não exibidos.
