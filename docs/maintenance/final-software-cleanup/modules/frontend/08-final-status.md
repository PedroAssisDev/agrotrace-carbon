# 08 — Status final — frontend

**Classificação:** `PROJETO INDEPENDENTE PRONTO` (com dependências de workspace)

## Critérios

| Critério | Status |
|----------|--------|
| README / pyproject / `.gitignore` | OK (1.0.0) |
| 8 rotas canônicas + 9 abas | OK |
| Legado ativo removido | OK (`LEGACY_REDIRECTS`, `include_legacy`, fallbacks `property_ids`/`period_mode`) |
| Testes | OK no env de workspace (96 passed na rodada de packaging) |

## Limitações

- Pytest em venv isolada do frontend exige `pip install -e` dos serviços irmãos (documentado).
- Regressão full (smoke + ciclo completo) não incluída no modo `--quick` pós-legado.
