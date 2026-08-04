# SQLite Schema

DDL source of truth: `schemas/sqlite/blockchain_service_schema.sql`

## Core tables

- `anchor_request`
- `evidence_package`
- `evidence_item`
- `hash_record`
- `blockchain_network`
- `blockchain_transaction`
- `anchoring_attempt`
- `verification_log`
- `audit_log`
- `observer_state`

## Bootstrap

```bash
python -m app.interfaces.cli init-db
```

Default network seeded: `local_simulated`
