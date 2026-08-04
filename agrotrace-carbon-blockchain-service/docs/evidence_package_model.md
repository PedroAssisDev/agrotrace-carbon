# Evidence Package Model

## Package types

- `monthly_carbon_result`
- `annual_carbon_result`
- `daily_to_monthly_aggregation`
- `monthly_to_annual_aggregation`
- `ontology_publication`
- `manual_audit_package`

## Item types

- `calculation_method_version`
- `parameter_set`
- `approved_result`
- `publication_receipt`
- `aggregation_link`
- `local_hash_ref`

## Status lifecycle

`draft -> ready_to_anchor -> anchoring -> anchored -> verified`

Sensitive farm data must not be copied into evidence payloads. Only hashes and scoped identifiers are allowed.
