# Testing Guide

## Unit tests

- `tests/unit/test_hash_and_merkle.py`
- canonical JSON determinism
- SHA-256 determinism
- Merkle root determinism and odd leaf handling

## Integration tests

- `tests/integration/test_e2e_flow.py`
- observe -> build -> simulate -> verify

## Contract tests

- `tests/test_anchor_payload_schema.py` (requer `jsonschema` do extra `dev`)

Install:

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

Não use `--ignore=tests/test_anchor_payload_schema.py` — o teste deve ser coletado normalmente após instalar o extra `dev`.
