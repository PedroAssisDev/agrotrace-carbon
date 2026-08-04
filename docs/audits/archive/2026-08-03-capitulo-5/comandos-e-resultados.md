# Comandos e resultados — Auditoria Capítulo 5

**Data da auditoria:** 2026-08-03  
**Ambiente:** Windows 10 (`win32 10.0.26200`), PowerShell  
**Python:** `C:\Users\PedroAssis\Documents\agrotrace-carbon\.venv\Scripts\python.exe` — 3.11.9  
**pytest:** 9.0.3  
**Foundry/Anvil:** 1.7.1  
**Git:** disponível no sistema, porém o diretório do projeto **não** é repositório Git (`fatal: not a git repository`)  
**Backup de salvaguarda:** `C:\Users\PedroAssis\AppData\Local\Temp\agrotrace-audit-backup-20260803-104947`  
**Logs brutos:** `%TEMP%\agrotrace-audit-logs\`

Regra desta auditoria: nenhum comando é declarado como aprovado sem ter sido executado nesta sessão. Scripts destrutivos (`reset_test_environment.py --confirm`, `wipe_test_data.py`, `approve_all_pending_cycles.py`) **não** foram executados.

---

## 1. Inventário “antes”

| Item | Valor |
|------|-------|
| `frontend/data/cycles` | 454 |
| `frontend/data/normalized` | 454 |
| `frontend/data/ontology_exports` | 908 |
| `frontend/data/properties` | 77 |
| `frontend/data/publications` | 1 (apenas `.gitkeep`) |
| `frontend/data/evidence_packages` | 0 |
| `frontend/data/db/provenance.db` | 35 tabelas; 453 reviews `pending`; 453 result sets `preliminary`; 0 publicações; 0 `audit_blockchain_anchor` |
| `frontend/data/db/blockchain_service.db` | apenas `blockchain_network` = 3 |
| `agrotrace-carbon-blockchain-service/data/blockchain_service.db` | 3 pacotes, 2 txs, 26 verification_log |
| `reporting_period.period_granularity` | somente `monthly` (42) |
| Papéis PROV | executor 907, integrator 453, reviewer 453; **publisher ausente** |

Snapshot JSON: `docs/auditoria-capitulo-5/_inventory_before.json`.

---

## 2. Suítes de teste

| # | Suite | Diretório | Comando | Exit | Resultado | Tempo |
|---|-------|-----------|---------|------|-----------|-------|
| 1 | ontology-manager | `agrotrace-carbon-ontology-manager` | `python -m pytest -q --tb=line` | 0 | **14 passed** | 4,1 s |
| 2 | calculation-service | `agrotrace-carbon-calculation-service` | `python -m pytest -q --tb=line` | 0 | **43 passed** | 2,2 s |
| 3 | wrappers-service | `agrotrace-carbon-wrappers-service` | `python -m pytest -q --tb=line` | 0 | **41 passed, 3 skipped**, 2 warnings | 2,1 s |
| 4 | model-training | `agrotrace-carbon-model-training-service` | `python -m pytest -q --tb=line` | 0 | **50 passed** | 30,4 s |
| 5 | traceability-service | `agrotrace-carbon-traceability-service` | `python -m pytest -q --tb=line` | 0 | **104 passed**, 1 warning | 40,1 s |
| 6 | frontend | `frontend` | `python -m pytest tests/ -q --tb=line` | 0 | **22 passed** | 4,4 s |
| 7 | save-file | `agrotrace-carbon-save-file` | `python -m unittest discover -s tests -v` | 0 | **4 passed** | 0,3 s |
| 8a | blockchain (1ª tentativa) | `agrotrace-carbon-blockchain-service` | `python -m pytest tests/ -m "not blockchain_local and not sepolia" -q --tb=line` | 2 | **ERROR collection** — `ModuleNotFoundError: jsonschema` em `tests/test_anchor_payload_schema.py` | 4,4 s |
| 8b | blockchain (reexecução) | idem | idem + `--ignore=tests/test_anchor_payload_schema.py` | 0 | **41 passed, 4 deselected**, 1 warning | 5,7 s |
| 9 | forge contracts | `agrotrace-carbon-blockchain-service/contracts` | `forge build && forge test -vvv` | 0 | **9 passed**, 0 failed | 3,6 s |

**Totais aproximados de testes verdes nesta sessão:** 14+43+41+50+104+22+4+41+9 = **328 passed** (+ 3 skipped wrappers; + 4 deselected blockchain markers; + 1 teste schema não executável por dependência ausente).

**Não executados (escopo acordado):** pytest `-m blockchain_local`, pytest `-m sepolia`, Anvil deploy, nova ancoragem Sepolia.

---

## 3. Scripts `validate_*` (frontend)

Executados a partir de `frontend/` com `python scripts/<nome>.py`.

| Script | Exit | Resultado resumido | Tempo (ms) |
|--------|------|--------------------|------------|
| `validate_pending_approval_seed.py` | 1 | FAIL — fila/count_pending esperado 17 (ambiente com centenas de pendências) | 2818 |
| `validate_frontend_pipeline.py` | 0 | **PASS** | 128648 |
| `validate_global_filter.py` | 0 | **PASS** | 9693 |
| `validate_property_filter.py` | 1 | FAIL — rótulo 1 prop esperado nome ≠ “Embrapa P-1” | 6822 |
| `validate_dashboard_indicators.py` | 0 | **PASS** | 1868 |
| `validate_temporal_model.py` | 1 | FAIL — Jan–Jun 6≠7; `FARM-DAILY-001` com 0 ciclos | 6808 |
| `validate_calculation_review.py` | 1 | 35 OK / 1 FAIL — ciclo ANNUAL sem `factors_used` usa subcálculo | 12498 |
| `validate_technical_audit.py` | 1 | 19 OK / 1 FAIL — `TechnicalActionsPanel` colapsado | 6511 |
| `validate_provenance_queries.py` | 0 | **25 OK, 0 FAIL** | 5754 |
| `validate_forecast_page.py` | 0 | **OK** | 7614 |
| `validate_ontology_domain_source.py` | 0 | **OK** | 884 |
| `validate_final_pipeline.py` | 0 | **35 OK, 0 FAIL** | 248953 |

**Resumo:** 7 PASS / 5 FAIL entre os 12 scripts priorizados.

---

## 4. Ponta a ponta (ciclos novos)

| Script | Exit | Resultado | Tempo |
|--------|------|-----------|-------|
| `scripts/run_pipeline_smoke_test.py` | 0 | **Smoke OK** — upload → preservação → pending → cálculo preliminar → finalize → publicação → evidence → anchoring → verified (`VERIFICADO / ÍNTEGRO`); blockchain locked antes; publicação idempotente | 249,7 s |
| `scripts/test_full_emission_cycle.py` | 0 | **PASS** — auto pós-ingestão; auto pós-aprovação; rejeição OK; guard cálculo; **guard blockchain** (`BLOCKCHAIN_LOCKED` sem publicação) | 450,1 s |

### Integridade dos 454 ciclos pendentes

| Métrica | Valor |
|---------|-------|
| Backup cycles | 454 |
| Current cycles após validate+e2e | 463 |
| Ausentes do current vs backup | **0** |
| Extras gerados | 9 |
| Conclusão | Os 454 ciclos originais foram **preservados** |

### Inventário parcial “depois” (proveniência)

| Métrica | Depois |
|---------|--------|
| `calculation_review` | approved=3, pending=459, rejected=1 |
| `result_set_status` | approved=3, preliminary=456 |
| `calculation_result_publication_execution` | 3 |
| Papel `publisher` | 3 |
| Outbox publicação | `APPROVED_RESULT_PUBLISHED`=4; `result_publication.published`=3 |
| `frontend/.../blockchain_service.db` | evidence_package=4, blockchain_transaction=4, verification_log=16 |
| `frontend/data/publications` | 4 manifests (+ `.gitkeep`) |
| `frontend/data/evidence_packages` | 4 |

---

## 5. Interface (UI)

| Verificação | Resultado |
|-------------|-----------|
| Import bootstrap + `ROUTES` + layout + callbacks | EXIT=0 — 8 rotas listadas; `LAYOUT_OK`; `CALLBACKS_IMPORT_OK` |
| `python main.py` (PID 24016) | Servidor iniciou |
| HTTP GET `http://127.0.0.1:8050` + 7 rotas | **Todas STATUS=200** (`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`, `/technical-audit`, `/settings`) |
| Encerramento | `SERVER_STOPPED` |

Observação: o conteúdo HTML inicial das rotas Dash é o shell da aplicação (mesmo `LEN≈6165` no GET inicial); a renderização por pathname ocorre via callback. O carregamento HTTP 200 confirma operabilidade do servidor e das rotas registradas.

---

## 6. Artefatos blockchain pré-existentes (não reexecutados on-chain)

Escopo acordado: **sem gas / sem nova transação Sepolia / sem deploy Anvil**.

| Artefato | Local | Status |
|----------|-------|--------|
| Validação interativa Sepolia | `agrotrace-carbon-blockchain-service/evidence/sepolia/interactive_validation_20260731_153031/summary.json` | `overall: SUCCESS` / `PASSOU` em 23 itens (gate, off-chain, âncora/idempotência, recibo, evento, consulta, on-chain, adulteração, revalidação) |
| Tx / bloco | `transaction_hash=0xca2d00fa…`, `block_number=11390296`, `chain_id=11155111` | Registrados no summary (valores públicos on-chain) |
| Contrato | `0x7dFc5d077c0911DcD29881aEf4B4EF5FFc1573Aa` | Presente |
| forge | 9 testes Solidity | PASS nesta sessão |

---

## 7. Dependências relevantes observadas

| Pacote | Situação |
|--------|----------|
| dash, plotly, pandas, owlready2, sqlalchemy, web3, fastapi, sklearn, etc. | Presentes no `.venv` |
| `jsonschema` | **Ausente** — bloqueou coleta de `test_anchor_payload_schema.py` |
| Pacotes editáveis | `agromrv-o-lite`, `agrotrace-carbon-blockchain-service`, `agrotrace-carbon-provenance-service`, `carbonseco-model-training-service` |
| Anvil env | `BLOCKCHAIN_ANVIL_PRIVATE_KEY` e `CONTRACT_ADDRESS` **EMPTY** — testes `blockchain_local` fora de escopo |

---

## 8. Comandos deliberadamente não executados

- `python scripts/reset_test_environment.py --confirm`
- `python scripts/wipe_test_data.py`
- `python scripts/reset_and_seed_pending_cycles.py --confirm`
- `python scripts/approve_all_pending_cycles.py`
- `python scripts/seed_test_scenarios.py`
- `python scripts/validate_ontology_parameter_lifecycle.py` (mutante)
- `pytest -m blockchain_local` / `-m sepolia`
- Nova ancoragem Sepolia / deploy Anvil
