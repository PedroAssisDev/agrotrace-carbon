# 05 — Verificação de legado ativo

**Ferramenta:** `tooling/verify_no_active_legacy.py`  
**Resultado JSON:** `05-legacy-verification.json`

```text
legacy_active_count = 0
deprecated_api_count = 0
legacy_redirect_count = 0
unversioned_abi_count = 0
duplicate_schema_count = 0
```

Removido do runtime:

- `TemporalScope.YEARLY` e string canônica `"yearly"`
- `LEGACY_REDIRECTS`
- `include_legacy`
- `process_file_auto`
- `get_period_mode` / `period_mode`
- fallback `property_ids` → `farm_id`

Histórico permanece em `academic-evidence/` e docs de arquivo (não contam).
