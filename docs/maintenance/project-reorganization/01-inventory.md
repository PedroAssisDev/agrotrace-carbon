# 01 — Inventário completo (FASE 1)

**Escopo:** arquivos autorais e artefatos relevantes.  
**Excluídos do inventário detalhado:** `.venv`, `node_modules`, `.git`, caches, `__pycache__`, `.pytest_cache`, `contracts/lib`, `*.egg-info`.  
**Método:** listagem de árvore, glob, grep de referências, leitura de entrypoints e auditorias existentes.  
**Confiança global:** média-alta para estrutura; baixa para uso de cada arquivo gerado sob `data/`.

---

## 1. Código Python (~729 `.py`)

| Área | Caminho | Finalidade |
|------|---------|------------|
| Frontend | `frontend/` (~286) | Dash UI, callbacks, adapters, orchestrator, scripts |
| Blockchain | `agrotrace-carbon-blockchain-service/app/` | Domínio, use cases, EVM, SQLite, CLI, worker |
| Traceability | `agrotrace-carbon-traceability-service/` | Proveniência, UoW, FastAPI opcional |
| Wrappers | `agrotrace-carbon-wrappers-service/` | Normalização por layouts |
| Ontology | `agrotrace-carbon-ontology-manager/ontology/` | Schema OWL, população, validação |
| Calculation | `agrotrace-carbon-calculation-service/` | Fórmulas IPCC/ECOFARM, pipeline |
| Model training | `agrotrace-carbon-model-training-service/src/` | Treino e registry de modelos |
| Save-file | `agrotrace-carbon-save-file/save_file/` | Preservação + SHA-256 |
| Auditoria tools | `docs/auditoria-pos-implementacao/_gen_reports.py` | Geração de MD a partir de JSON |

**Entrypoints:** `frontend/main.py`; `python -m app.interfaces.cli` (blockchain); `model_training_service.cli`; scripts em `frontend/scripts/`.

---

## 2. Frontend Dash

| Item | Valor |
|------|-------|
| Entrypoint | `frontend/main.py` |
| Rotas canônicas | `/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`, `/technical-audit`, `/settings` |
| Redirects legados | `LEGACY_REDIRECTS` em `frontend/pages/router.py` |
| Abas auditoria | 9 (`ta-summary` … `ta-payload`) em `technical_audit.py` |
| Orquestração | `frontend/services/local_orchestrator.py` |
| Adapters | `*_adapter.py` sob `frontend/services/` |
| README | `frontend/README.md` |

---

## 3. Módulos e serviços

| Módulo | Pasta | README |
|--------|-------|--------|
| save-file | `agrotrace-carbon-save-file/` | sim |
| wrappers | `agrotrace-carbon-wrappers-service/` | sim + docs densos |
| ontology | `agrotrace-carbon-ontology-manager/` | sim |
| calculation | `agrotrace-carbon-calculation-service/` | sim (mínimo) |
| model-training | `agrotrace-carbon-model-training-service/` | sim |
| traceability | `agrotrace-carbon-traceability-service/` | sim |
| blockchain | `agrotrace-carbon-blockchain-service/` | sim |
| frontend | `frontend/` | sim |

---

## 4. Testes

| Local | Tipo |
|-------|------|
| `*/tests/` por serviço | unit / integration |
| `frontend/tests/` | pytest (~20 arquivos) |
| `contracts/test/*.t.sol` | Forge |
| `docs/auditoria-pos-implementacao/tests/` | gerador de relatórios |
| `frontend/scripts/test_full_emission_cycle.py` | ciclo E2E |

---

## 5. Scripts `validate_*` (25)

Em `frontend/scripts/`:

`validate_analytic_context`, `validate_calculation_review`, `validate_correction_recalculation`, `validate_dashboard_indicators`, `validate_emission_calculation_details`, `validate_emulated_import`, `validate_executive_temporal`, `validate_farm_registry`, `validate_final_pipeline`, `validate_forecast_page`, `validate_frontend_pipeline`, `validate_general_analysis`, `validate_global_filter`, `validate_maintainability_extensibility`, `validate_ontology_domain_source`, `validate_ontology_parameter_lifecycle`, `validate_pending_approval_seed`, `validate_prediction_separation`, `validate_preliminary_calculation_form`, `validate_preliminary_calculation_view`, `validate_property_filter`, `validate_provenance_queries`, `validate_reproducibility`, `validate_technical_audit`, `validate_temporal_model`.

**Orquestrador:** `run_full_regression.py` (glob de todos `validate_*.py`).

---

## 6. Scripts operacionais

| Script | Papel |
|--------|-------|
| `reset_test_environment.py` | Reset (destrutivo; exige `--confirm`) |
| `seed_test_scenarios.py` | 3 cenários oficiais |
| `run_pipeline_smoke_test.py` | Smoke |
| `test_full_emission_cycle.py` | Ciclo + gate |
| `reset_and_seed_pending_cycles.py` / `approve_all_pending_cycles.py` | Seed/aprovação em massa |
| `wipe_test_data.py` | Wrapper do reset |
| `import_emulated_uploads.py` | Import Embrapa/emulado |
| `migrate_*`, `backfill_*` | Manutenção one-shot (UNCERTAIN) |
| `generate_audit_reports.py` | Matriz Cap. 5 a partir de YAML + regressão |
| `scan_secrets.py` | Varredura de segredos |
| Blockchain `scripts/` | init_db, worker, ABI export, sepolia smoke, verify |

---

## 7. Configurações

| Arquivo | Local |
|---------|-------|
| `.env.example` | raiz, blockchain, traceability |
| `.gitignore` | raiz |
| `pyproject.toml` | blockchain, calculation, ontology, traceability, model-training |
| `requirements.txt` | frontend, wrappers |
| `foundry.toml` | `blockchain-service/contracts/` |
| `training.yaml` | model-training `configs/` |
| `frontend/config.py` | flags e paths runtime |
| `agrotrace-carbon.code-workspace` | workspace VS Code/Cursor |

---

## 8. Layouts YAML/JSON

- Wrappers: layouts versionados (`intraday:v1`, `monthly:v1`, `annual:v1`) sob o pacote wrappers.
- `docs/auditoria-capitulo-5/requirements_map.yaml` — mapa RF/RNF (divergente).
- Exemplos JSON blockchain: `data/examples/*.example.json(c)`.

---

## 9. Ontologias

| Tipo | Local |
|------|-------|
| Código schema/população | `agrotrace-carbon-ontology-manager/ontology/` |
| Docs | `docs/ontology_agromrv_lite.md` (ontology-manager) |
| Exports OWL/TTL | `frontend/data/ontology_exports/` — **GENERATED** (~centenas) |

---

## 10. Schemas

| Path | Nota |
|------|------|
| `agrotrace-carbon-blockchain-service/schemas/json/*.schema.json` | evidence, item, anchor |
| `schemas/anchor_payload.schema.json` | **DUPLICATE path** vs `schemas/json/` (teste usa raiz `schemas/`) |
| `schemas/canonical/` | vectors + rules |
| `schemas/sqlite/blockchain_service_schema.sql` | DDL |

---

## 11. SQL e bancos

| Item | Classificação |
|------|---------------|
| Schemas SQL (blockchain, demos traceability) | CANONICAL / TEST |
| `frontend/data/db/*.db` | OPERACIONAL / GENERATED (gitignored) |
| Triggers append-only | documentados em `docs/architecture/append-only-tables.md` |

---

## 12–14. Solidity, ABI, evidências

| Artefato | Path |
|----------|------|
| Contrato | `contracts/src/CarbonEvidenceRegistry.sol` |
| Teste Forge | `contracts/test/CarbonEvidenceRegistry.t.sol` |
| Deploy script | `contracts/script/DeployCarbonEvidenceRegistry.s.sol` |
| Deployment Sepolia | `contracts/deployments/sepolia.json` (+ schema) |
| ABI | `app/infrastructure/anchoring/contracts/*.abi.json` (+ `.v1.0.0`) |
| Evidências runtime | gitignored sob `evidence/`; artefatos de validação interativa = ACADEMIC-EVIDENCE |

---

## 15. Documentos Markdown (~108)

Ver inventário detalhado e ações em `03-markdown-audit.md`.

Grupos: raiz (2), `docs/` (41), blockchain (~21), wrappers (~25), traceability (7), model-training (5), calculation (2), ontology (~2), frontend (1), save-file (1), caches README ignoráveis.

---

## 16. ADRs (3)

- `docs/decisions/ADR-001-frontend-as-interface-and-orchestrator.md`
- `docs/decisions/ADR-002-in-process-modular-integration.md`
- `docs/decisions/ADR-003-approval-publication-and-blockchain-gate.md`

---

## 17. Relatórios de auditoria

| Pasta | Papel | Status |
|-------|-------|--------|
| `docs/audit/` | Tópicos estáveis | referência (parcialmente stale) |
| `docs/auditoria-capitulo-5/` | Cap. 5 Aug 3 | HISTORICAL |
| `docs/auditoria-capitulo-5/final/` | Snapshot auto Aug 4 AM | GENERATED / HISTORICAL |
| `docs/auditoria-pos-implementacao/` | Pós-implementação Aug 4 PM | **CURRENT** |

---

## 18. Documentação acadêmica

| Fonte | Situação |
|-------|----------|
| Dissertação PDF/LaTeX | **Ausente** do repo (`frontend/main (7).pdf` citado) |
| RF/RNF/CE alinhados | `09-resultados.json`, `03-matriz-requisitos.md`, `05-cenarios-ce1-ce5.md` |
| Extrato em prompt | `PROMPT-AUDITORIA-CURSOR.md` |
| Texto-base Cap. 5 | `texto-base-capitulo-5.md` |

---

## 19. Dados de exemplo

| Path | Tipo |
|------|------|
| `agrotrace-carbon-save-file/data/embrapa/` | CSVs-fonte Embrapa (`SAMPLE_DATA_DIR`: annual/monthly/daily_report.csv) |
| `agrotrace-carbon-save-file/data/emulated_uploads/` | fixtures |
| `blockchain-service/data/examples/` | payloads exemplo |
| `model-training-service/examples/` | CSV exemplo |

---

## 20. Temporários e gerados (não inventariar arquivo a arquivo)

| Path | Nota |
|------|------|
| `frontend/data/**` | cycles, DBs, normalized, ontology, evidence, publications, logs — gitignored |
| `save-file/data/originals/` | preservados — gitignored |
| `model-training-service/artifacts/` | modelos — gitignored |
| `.pytest_cache/`, `__pycache__/` | cache |

---

## Estado Git (inventário operacional)

- Branch: `master`
- Commits: **0**
- Staged: `docs/auditoria-pos-implementacao/03-matriz-requisitos.md`
- Restante: untracked

## Próximo documento

Classificação por grupos: `02-file-classification.md`.
