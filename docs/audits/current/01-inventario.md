# Inventário da auditoria

## Repositório

- Raiz: `agrotrace-carbon` (workspace)
- Branch: `master`
- Commits: **0** (working tree 100% untracked)
- HEAD: *inexistente*

## Versões

- Python sistema: 3.13.5
- Python venv: **3.11.9** (usado na regressão)
- pytest: 9.0.3
- Foundry/Forge: 1.7.1 (commit 4072e487…)

## Módulos / serviços

- `frontend/` — Dash orquestrador
- `agrotrace-carbon-save-file/`
- `agrotrace-carbon-wrappers-service/`
- `agrotrace-carbon-ontology-manager/`
- `agrotrace-carbon-calculation-service/`
- `agrotrace-carbon-model-training-service/`
- `agrotrace-carbon-traceability-service/`
- `agrotrace-carbon-blockchain-service/` (+ `contracts/`)
- `docs/`, `data/` (amostras), `logo/`

## Dependências

- `agrotrace-carbon-blockchain-service/pyproject.toml` inclui `jsonschema>=4.0`
- `tests/test_anchor_payload_schema.py` presente (coletável)
- `.env.example` versionado com placeholders (valores mascarados na auditoria)
- `.env` ignorado por `.gitignore`

## AGROTRACE_DATA_ROOT

- Leitor canônico único: `frontend/config.py`
- Isolamento: `frontend/scripts/_validation_env.py`, `frontend/tests/conftest.py`, `run_full_regression.py`
- Bypass: `save_file/storage.py::default_originals_dir()` (adapter passa `dest_dir`); `mock_data.py` paths fixos; samples/model-training fora do root

## Rotas frontend (8)

`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`, `/technical-audit`, `/settings`  
Legado → `/technical-audit`. Abas auditoria: 9 (`ta-summary` … `ta-payload`).

## Bancos / artefatos operacionais (antes)

| Área | Observação |
|------|------------|
| cycles | 469 arquivos (~27 MB) |
| db | provenance.db + blockchain_service.db (+ wal/shm) |
| publications | 8 arquivos |
| ontology_exports / normalized / logs | presentes |

Hashes baseline (SHA-256):

- `blockchain_service.db` = `C0B9CAFF…A2645`
- `provenance.db` = `E8CB58F9…CD1C8`

## Canonicalização

- Fonte oficial: `agrotrace-carbon-blockchain-service/app/domain/services/canonical_json_service.py` (`json_canonical_v1`)
- Frontend: `frontend/utils/hash_helpers.py` fail-closed (`CanonicalizationUnavailableError`)
- Vetores: `schemas/canonical/canonical_vectors.json`

## VersionManifest

- `frontend/services/version_manifest_service.py` — campos com `missing_reason` explícito

## Suítes / scripts

- pytest por serviço + `frontend/tests/`
- Forge `contracts/`
- 24 `frontend/scripts/validate_*.py`
- `run_pipeline_smoke_test.py`, `test_full_emission_cycle.py`, `scan_secrets.py`, `run_full_regression.py`

## Divergência documental

`docs/auditoria-capitulo-5/requirements_map.yaml` **não** segue a numeração oficial do PDF (ex.: RF004/RF006/RF007). PDF prevalece.
