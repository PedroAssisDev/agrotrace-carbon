# Anchor Payload

See also `docs/anchor_payload_model.md` and examples in `data/examples/`.

## Required fields

- `schema_version`
- `package_id_hash`
- `package_type`
- `period_start`, `period_end`, `period_granularity`
- `merkle_root`
- `metadata_hash`
- `public_summary_enabled`
- `anchoring_status`
- `anchoring_mode`

## Optional public result

When `public_summary_enabled=true`:

```json
{
  "result_type": "gross_emission",
  "total_emission_scaled": 155250,
  "unit": "kgCO2e",
  "scale": 1000
}
```

`155250` with `scale=1000` means `155.25 tCO2e`.
