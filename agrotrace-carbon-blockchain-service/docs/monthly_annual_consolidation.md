# Monthly and Annual Consolidation

## Monthly package

Triggered by:

- `MONTHLY_RESULT_CONSOLIDATED`
- `CALCULATION_APPROVED` with `result_scope=monthly`

## Annual package

Triggered by:

- `ANNUAL_RESULT_CONSOLIDATED`
- `CALCULATION_APPROVED` with `result_scope=annual`

## Aggregation packages

- `DAILY_DATA_AGGREGATED_TO_MONTHLY` -> `daily_to_monthly_aggregation`
- `MONTHLY_DATA_AGGREGATED_TO_ANNUAL` -> `monthly_to_annual_aggregation`

Aggregation items reference parent/child result set IDs only, never full result payloads.
