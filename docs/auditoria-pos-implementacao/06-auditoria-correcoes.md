# Auditoria das correções pós-auditoria anterior

| Correção | Evidência estática | Evidência executada | Status |
|----------|--------------------|---------------------|--------|
| Isolamento AGROTRACE_DATA_ROOT | `config.py`, `_validation_env`, conftest | regressão inteira em temp root; DBs ops intactos | ATENDIDO |
| Recuperação do bruto RF002 | `retrieve_original`, adapter, painel artefatos | save-file + technical_audit PASS | ATENDIDO |
| Lot / granularidades | enums OK; **OWL sem Lot** | temporal_model PASS | PARCIAL |
| Explicabilidade | `calc_explanation_v1`; factors anual testados | emission_details FAIL (série por gás) | PARCIAL |
| Proveniência→blockchain | adapters; gate; linkage view | full cycle PASS | ATENDIDO |
| Correção/recálculo | `result_correction_service`; `prov_core_prov_revision` | validate_correction PASS | ATENDIDO |
| Auditoria técnica | 9 abas `/technical-audit` | validate_technical_audit PASS | ATENDIDO |
| Append-only | triggers SQLite ambos serviços | testes invariants/unit inclusos nas suítes | ATENDIDO (parcial por tabela) |
| VersionManifest | campos + missing_reason | frontend tests | ATENDIDO |
| Reprodutibilidade | numérica + cripto | validate_reproducibility PASS | ATENDIDO |
| Manutenibilidade/extensibilidade | script dedicado | PASS | ATENDIDO |
| Credenciais | gitignore, .env.example, scan | scan_secrets PASS | ATENDIDO |
| Canonicalização única | blockchain-service SoT; fail-closed | canonical parity em frontend_tests | ATENDIDO |
| Predição | `PredictionNotPublishableError` | validate_prediction_separation PASS | ATENDIDO |
