# Matriz de requisitos (PDF oficial)

Fonte acadêmica: `frontend/main (7).pdf` §4.2.1–4.2.2.  
Evidências: inspeção estática + `_regressao.json` desta auditoria.

## RF001–RF021

| ID | Título | Status | Confiança | Teste | Lacunas |
|----|--------|--------|-----------|-------|---------|
| RF001 | Entrada de dados agropecuarios | ATENDIDO | alto | run_pipeline_smoke_test PASS | — |
| RF002 | Preservacao e recuperacao dos dados brutos | ATENDIDO | alto | save-file + validate_technical_audit PASS | — |
| RF003 | Normalizacao e padronizacao | ATENDIDO | alto | wrappers 41p + validate_frontend_pipeline PASS | — |
| RF004 | Validacao qualidade/consistencia | ATENDIDO | medio | wrappers + ontology validation PASS | — |
| RF005 | Granularidades temporal e organizacional | PARCIALMENTE ATENDIDO | alto | validate_temporal_model PASS; Lot OWL ausente | OWL sem Lot |
| RF006 | Registro de proveniencia | ATENDIDO | alto | traceability 115p + validate_provenance_queries PASS | — |
| RF007 | Ontologia de trabalho | ATENDIDO | alto | ontology 14p + validate_ontology_* PASS | — |
| RF008 | Calculo preliminar | PARCIALMENTE ATENDIDO | alto | calculation 53p; validate_emission_calculation_details FAIL; validate_preliminar | validate_emission_calculation_details / preliminary_form |
| RF009 | Registro dos parametros | PARCIALMENTE ATENDIDO | medio | test_calculation_explanation; emission_details FAIL serie por gas | validate_emission_calculation_details / preliminary_form |
| RF010 | Correcao, recalculo e nova versao | ATENDIDO | alto | validate_correction_recalculation PASS | — |
| RF011 | Predicao de emissoes e producao | ATENDIDO | alto | validate_prediction_separation PASS | — |
| RF012 | Metricas e indicadores | ATENDIDO | medio | validate_dashboard_indicators PASS | — |
| RF013 | Revisao humana | ATENDIDO | alto | validate_calculation_review PASS | — |
| RF014 | Decisao individual | ATENDIDO | alto | validate_calculation_review PASS | — |
| RF015 | Aprovacao geral | ATENDIDO | alto | validate_pending_approval_seed + full cycle PASS | — |
| RF016 | Publicacao ontologia final | ATENDIDO | alto | test_full_emission_cycle + ontology lifecycle PASS | — |
| RF017 | Pacote de evidencias | ATENDIDO | alto | test_full_emission_cycle PASS | — |
| RF018 | Identificadores criptograficos | ATENDIDO | alto | frontend_tests canonical + validate_reproducibility PASS | — |
| RF019 | Ancoragem blockchain | ATENDIDO | medio | forge 9p + blockchain 59p + full cycle PASS; Sepolia documental | Sepolia nao reexecutada; evidencia documental preexistente |
| RF020 | Visualizacao e auditoria tecnica | ATENDIDO | medio | validate_technical_audit PASS; captura visual Cap.5 pendente | Capturas visuais Cap.5 pendentes |
| RF021 | Consulta e verificacao evidencia | ATENDIDO | medio | full cycle + integrity paths PASS | — |

### Contagem RF
`{"ATENDIDO": 18, "PARCIALMENTE ATENDIDO": 3}`

## RNF001–RNF012

| ID | Título | Status | Confiança | Teste | Lacunas |
|----|--------|--------|-----------|-------|---------|
| RNF001 | Rastreabilidade | ATENDIDO | alto | validate_provenance_queries + full cycle | — |
| RNF002 | Auditabilidade | ATENDIDO | medio | validate_technical_audit PASS | — |
| RNF003 | Manutenibilidade | ATENDIDO | medio | PASS | — |
| RNF004 | Integridade | ATENDIDO | alto | validate_reproducibility + full cycle | — |
| RNF005 | Explicabilidade | PARCIALMENTE ATENDIDO | medio | emission_details FAIL | serie por gas no validador |
| RNF006 | Consistencia semantica | PARCIALMENTE ATENDIDO | alto | temporal PASS; Lot OWL gap | Lot OWL |
| RNF007 | Operabilidade das interfaces | ATENDIDO | medio | validate_technical_audit + forecast/approval PASS | — |
| RNF008 | Extensibilidade | ATENDIDO | medio | validate_maintainability_extensibility PASS | — |
| RNF009 | Reprodutibilidade | ATENDIDO | alto | PASS | — |
| RNF010 | Versionamento | ATENDIDO | alto | frontend tests + audit payload | — |
| RNF011 | Interoperabilidade | ATENDIDO | medio | blockchain + forge PASS | — |
| RNF012 | Protecao credenciais / minimizacao on-chain | ATENDIDO | alto | scan_secrets PASS | — |

### Contagem RNF
`{"ATENDIDO": 10, "PARCIALMENTE ATENDIDO": 2}`

## Notas de classificação

- Existência de arquivo/classe **não** basta; status ATENDIDO exige teste ou comportamento executado nesta rodada.
- HTTP 200 de Dash **não** foi usado como prova de callbacks; usou-se `validate_technical_audit` e correlatos.
- Sepolia: evidência **documental preexistente**, não execução desta auditoria.
- `requirements_map.yaml` antigo diverge na numeração de quase todos os RF/RNF/CE (colisão de IDs RF004–RF008, RF012–RF017, RF019, RF021; CE3 YAML ≈ PDF CE4) — **PDF prevalece**; ver extrato do [Extract PDF RF/RNF criteria](39359bd8-6283-440a-9a5a-86f4c740a3cd).
- Decisões oficiais Cap. 4.2.3 = **9** (não 10); ver `04-decisoes-arquiteturais.md`.
