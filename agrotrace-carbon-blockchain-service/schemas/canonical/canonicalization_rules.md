# Canonicalization Rules

Method: `json_canonical_v1` (version `1`)

**Single official source:** `app/domain/services/canonical_json_service.py`

No other module may implement an independent strategy for official evidence hashes.
The frontend must import these functions (or consume hashes already computed by the service).
If the official implementation cannot be loaded, official hashing **must fail explicitly** —
never fall back to compact `json.dumps` or any alternate algorithm.

## Versioned dispatch

- Registry: `CANONICALIZATION_METHODS`
- API: `to_canonical_json_for(method, payload)`
- Missing/empty method on historical packages → assume `json_canonical_v1`
- Unknown method → `UnknownCanonicalizationError` (fail closed)
- Simulated and EVM modes use the **same** canonical bytes / hashes

## Rules (`json_canonical_v1`)

1. **Key ordering:** sort object keys lexicographically (`str` key) at every nesting level
2. **Lists:** preserve order (domain may sort by `item_order` before hashing packages)
3. **UTF-8 / Unicode:** `json.dumps(..., ensure_ascii=False)` — non-ASCII preserved (e.g. accents)
4. **Whitespace:** compact separators `(",", ":")` — no spaces
5. **null:** remains JSON `null`
6. **boolean:** remains JSON `true` / `false` (handled before number path)
7. **integers:** JSON integers
8. **decimals / floats:**
   - whole values (`1.0`, `Decimal("1.000")`) → JSON integer `1`
   - non-whole → decimal string without scientific notation
   - `NaN` / `Infinity` rejected
9. **numeric-looking strings** (e.g. `"1.0"`) remain strings — never coerced
10. **datetime:** UTC `YYYY-MM-DDTHH:MM:SSZ` via `format_instant` (no microseconds)
11. **date:** ISO `YYYY-MM-DD`
12. **unsupported types:** `CanonicalizationError` (no `default=str`)
13. Encode as UTF-8 bytes before hashing
14. Hash with SHA-256 → `0x` + 64 lowercase hex

## Equivalence examples

Same numeric form:

- `1`
- `1.0`
- `Decimal("1.000")`

A string `"1.0"` is **not** equivalent.

## Historical artifacts

Do not silently change semantics of `json_canonical_v1`. Introduce a new method name
(e.g. `json_canonical_v2`) when rules change. Verification reads the stored
`canonicalization_method` / `integrity_context.canonicalization_method`.

## Exclusions

Volatile fields must never enter canonical payloads used for integrity proofs
(processing timestamps, retry counters, lock metadata, internal status).

## Related (not official evidence)

- Traceability provenance hashes use label `prov_canonical_v1` (different algorithm).
- Frontend `ui_preview_hash` is display-only and must never feed evidence packages.
