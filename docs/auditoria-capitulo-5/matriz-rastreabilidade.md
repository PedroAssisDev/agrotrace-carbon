# Matriz de rastreabilidade — Auditoria Capítulo 5

**Data:** 2026-08-03  
**Artefato:** terceiro ciclo AgroTrace Carbon / MRV agropecuário  
**Legenda de status:** A = Atendido · P = Parcialmente atendido · N = Não atendido · NV = Não verificável · NA = Não aplicável

Contagens simples (sem índice ponderado):

| Grupo | A | P | N | NV | Total |
|-------|---|---|---|----|-------|
| RF001–RF021 | 15 | 6 | 0 | 0 | 21 |
| RNF001–RNF012 | 6 | 6 | 0 | 0 | 12 |
| RN-01–RN-10 | 8 | 2 | 0 | 0 | 10 |
| RE-01–RE-06 | 3 | 3 | 0 | 0 | 6 |
| **Total** | **32** | **17** | **0** | **0** | **49** |

Percentuais: Atendido 65,3%; Parcialmente atendido 34,7%; Não atendido 0%; Não verificável 0%.

---

## RF — Requisitos funcionais

| ID | Requisito | Critérios de aceitação | Tela/fluxo | Arquivos e símbolos | API/dados | Testes | Evidências | Status | Confiança | Lacunas |
|----|-----------|------------------------|------------|---------------------|-----------|--------|------------|--------|-----------|---------|
| RF001 | Entrada de dados | Dado associado a propriedade, período, ciclo e atividade | `/data-entry` → pipeline | `pages/data_entry.py`; `local_orchestrator.register_raw_upload` | cycles JSON; provenance `pipeline_source_artifact` | smoke PASS; validate_frontend_pipeline PASS | 454+ ciclos com contexto; HTTP 200 | A | alto | Seed diário escasso |
| RF002 | Preservação bruto | Artefato + metadados + hash; recuperação | `/data-entry`; save-file | `save_file.storage.save_original_*`; `sha256_file` | `save-file/data/originals/` + `.meta.json` | save-file 4p; smoke | Hash no ingresso; **sem retrieve API** | P | alto | Sem API de recuperação |
| RF003 | Normalização | Lote normalizado com contratos | wrappers na pipeline | `wrappers.process_file`; layouts `*:v1` | `frontend/data/normalized/` | wrappers 41p/3s; smoke | Layouts intraday/monthly/annual | A | alto | — |
| RF004 | Validação | Inconsistências bloqueiam etapas | wrappers + semantic | `validators/engine.py`; `run_semantic_step`; `can_run_calculation` | semantic_validation no cycle | wrappers; smoke; full cycle | Guardas de pipeline | A | médio | Suite negativa dedicada limitada |
| RF005 | Granularidades | daily/monthly/annual + animal/lote/property | layouts + ontologia | `TEMPORAL_GRANULARITIES`; OWL Property/Animal; **sem Lot** | reporting_period (só monthly no seed) | validate_temporal_model FAIL; ontology 14p | Lot ausente; daily=0 no seed | P | alto | Lot; daily seed; Jan–Jun 6≠7 |
| RF006 | Proveniência | Trajetória reconstruível | `/technical-audit` | `ProvenanceRecorder`; roles executor/integrator/reviewer/publisher | provenance.db | traceability 104p; validate_provenance_queries 25 OK | publisher=3 pós-e2e | A | alto | Link fraco com tx blockchain (RNF001) |
| RF007 | Ontologia trabalho | Instâncias AgroMRV-Lite no ciclo | ontology step | `build_full_ontology`; `populate_from_dataframe`; `export_ontology` | `ontology_exports/` working | ontology 14p; validate_ontology_domain_source OK | Working vs published paths | A | alto | Sem Lot |
| RF008 | Cálculo preliminar | Resultado preliminar; sem auto-publicação | `/calculations` | `compute_farm_period_emissions`; 4 fontes; GWP AR4 | result_set preliminary | calc 43p; smoke; full cycle | 456 preliminary pós-auditoria | A | alto | — |
| RF009 | Parâmetros de cálculo | Condições recuperáveis | detalhe de cálculo / revisão | `ProvenanceMetadata`; `to_flat_dict` sem fatores/GWP | parameter_set tables | calc 43p; validate_calculation_review 1 FAIL | factors_used anual falhou | P | alto | Fatores/GWP no flat dict |
| RF010 | Correção/recálculo | Nova versão preliminar + histórico | `/approval` | `request_correction`; `prov_revision` | revision table historicamente 0 | full cycle (rejeição); correção pouco exercitada | API existe; histórico fraco | P | médio | Cenário correção→recálculo pouco evidenciado |
| RF011 | Predição | Treino em aprovados/publicados; só consulta | `/previsoes` | `normalize_approved_results`; `PredictionFacade` | artifacts model-training | model 50p; validate_forecast_page OK | Separação de publicação | A | alto | — |
| RF012 | Métricas/indicadores | Indicadores derivados | `/` e `/indicators` | `indicator_service`; `build_dashboard_indicators` | analysis cycles | validate_dashboard_indicators PASS | KPIs/gráficos | A | alto | property_filter label FAIL |
| RF013 | Revisão humana | preliminar → em revisão | `/approval` | `ensure_review_started` | calculation_review | smoke; full cycle | 459 pending; seed count FAIL | A | alto | Expectativa seed=17 desatualizada |
| RF014 | Aprovação individual | Decisão por item + justificativa | `/approval` | `approve_item`; `reject_item`; `request_correction` | review items | full cycle; smoke | approved=3 rejected=1 | A | alto | — |
| RF015 | Aprovação geral | Bloqueio se obrigatório pendente | `/approval` | `can_finalize`; `finalize_file_approval` | approval step | smoke; full cycle | publication só após finalize | A | alto | — |
| RF016 | Publicação final | Só aprovados + ciclo aprovado | fluxo aprovação (redirect `/final-publication`→`/approval`) | `run_publication_step`; `publish_approved_cycle` | publications/; ontology final | validate_final_pipeline; smoke | 4 manifests; publication_exec=3 | A | alto | — |
| RF017 | Pacote de evidências | Pacote pós-publicação | pós-gate blockchain | `EvidencePackageBuilder`; `create_evidence_package` | evidence_packages/; blockchain DB | smoke; blockchain 41p | 4 pacotes pós-e2e | A | alto | Schema test sem jsonschema |
| RF018 | Hashes/Merkle | Canonical + hash + Merkle; divergência | verificação | `json_canonical_v1`; `sha256_hex`; `build_merkle_root` | hash_record; verification_log | forge; blockchain; smoke; Sepolia artifact | VERIFICADO/ÍNTEGRO; tamper Sepolia | A | alto | Distinguir sim vs EVM |
| RF019 | Ancoragem | Só pós-publicação; idempotência | Simulated no Dash; EVM em artefato | `BlockchainAnchorProviderPort`; `require_final_publication_event`; `CarbonEvidenceRegistry` | blockchain_transaction | full cycle gate; smoke; forge; Sepolia artifact | Gate BLOCKCHAIN_LOCKED; tx=4 simulado | A | alto | EVM Dash não reancorado nesta sessão |
| RF020 | Visualização/auditoria | Funções nas interfaces | 8 rotas (+ redirects) | `router.ROUTES`; `technical_audit` 9 abas | UI Dash | HTTP 200×8; validate_technical_audit 1 FAIL | 8≠12 telas; painel colapsado | P | alto | 8 vs 12; TechnicalActionsPanel |
| RF021 | Consulta/verificação | Match local↔chain; adulteração diverge | audit + verify | `VerifyAnchoredEvidenceUseCase`; smoke verify | verification_log | smoke; Sepolia artifact | Íntegro + tamper histórico | A | alto | Verify EVM via artefato, não nova tx |

---

## RNF — Requisitos não funcionais

| ID | Requisito | Critérios | Tela/fluxo | Arquivos/símbolos | API/dados | Testes | Evidências | Status | Confiança | Lacunas |
|----|-----------|-----------|------------|-------------------|-----------|--------|------------|--------|-----------|---------|
| RNF001 | Rastreabilidade | Trajetória até pacote/tx | audit + 2 DBs | ProvenanceRecorder; blockchain DB | provenance.db ≠ blockchain DB | smoke; e2e | publication ok; `audit_blockchain_anchor=0` | P | alto | Join manual entre stores |
| RNF002 | Auditabilidade | Consultas pela UI | `/technical-audit` | 9 abas; provenance SQL | UI | validate_provenance_queries OK; technical_audit 1 FAIL | Painel colapsado | P | alto | 1 FAIL UI |
| RNF003 | Manutenibilidade | Mudança localizada | — | ADR-001/002; adapters | módulos | suítes por serviço | SoC observado | A | médio | Sem experimento de alteração |
| RNF004 | Integridade | Original ok; tamper diverge | verify | VerifyAnchoredEvidenceUseCase; forge overwrite_reverts | verification_log | smoke; forge; Sepolia | Íntegro + tamper | A | alto | jsonschema ausente |
| RNF005 | Explicabilidade | Campos completos do cálculo | `/calculations` | ProvenanceMetadata; emission_detail | factors parciais | calc 43p; review 1 FAIL | Fatores/GWP flat incompletos | P | alto | Payload canônico incompleto |
| RNF006 | Consistência semântica | Vocabulário canônico | ontology | AgroMRV-Lite validators | OWL | ontology 14p | Sem Lot | P | alto | Lot |
| RNF007 | Operabilidade | Funções via UI | 8 rotas | router/sidebar | HTTP 200 | UI check; validates | Operável | A | médio | 1 FAIL audit panel |
| RNF008 | Extensibilidade | Pontos de extensão | layouts/providers | LayoutRegistry YAML; AnchorProviderPort | — | wrappers; blockchain | Providers pluggáveis | A | alto | — |
| RNF009 | Reprodutibilidade | Mesmo hash/Merkle; mesmo resultado | canonical | json_canonical_v1 | — | hash/merkle tests; smoke | Crypto forte; double-run CO2e fraco | A | médio | Double-run numérico |
| RNF010 | Versionamento | Versões recuperáveis | manifesto/ciclo | layout v1; METHOD_VERSION; sepolia contract_version; ABI sem filename version | — | estático + e2e | ABI não filename-versioned | P | alto | Mapa unificado de versões |
| RNF011 | Interoperabilidade | Contratos estruturados + ABI | pipeline | adapters; ABI JSON | artefatos | smoke; Sepolia artifact | Sem HTTP Dash | A | alto | — |
| RNF012 | Credenciais / minimização | Segredos externos; on-chain mínimo | .env + contrato | CarbonEvidenceRegistry fields; BLOCKCHAIN_*_PRIVATE_KEY SET | .env (valores omitidos) | inspeção nomes; contrato | Repo sem Git → ignore N/V | P | médio | Git ausente; varredura logs |

---

## RN — Regras de negócio / decisões

| ID | Decisão | Status | Confiança | Evidência-chave | Lacunas |
|----|---------|--------|-----------|-----------------|---------|
| RN-01 | Separação serviços | A | alto | ADR-001/002; adapters; suítes isoladas | — |
| RN-02 | Separação de estados | P | médio | result_lifecycle; aprovação | Nomenclatura “em revisão/rejeitado” vs ontology |
| RN-03 | Cálculo × predição | A | alto | `/previsoes`; treino só approved/published | Teste negativo dedicado |
| RN-04 | Proveniência × blockchain | A | alto | Gate; DBs separados; ADR-003 | — |
| RN-05 | Provider port | A | alto | BlockchainAnchorProviderPort; Simulated/Evm | — |
| RN-06 | Canonicalização única | A | alto | json_canonical_v1 compartilhado | Fallback compact JSON |
| RN-07 | Gate publicação final | A | alto | full cycle BLOCKCHAIN_LOCKED; ELIGIBLE_ANCHOR_EVENT_TYPES | Alias de nomes |
| RN-08 | Idempotência / no overwrite | A | alto | idempotency_key SHA256(network:package_hash); evidence_key keccak; forge overwrite_reverts | Distinção das duas chaves na dissertação |
| RN-09 | Minimização on-chain | A | alto | AnchorRecord 5 campos | — |
| RN-10 | Publicação na aprovação | A | alto | LEGACY `/final-publication`→`/approval` | — |

---

## RE / CE — Avaliação

| ID | Cenário | Status | Confiança | Evidências | Lacunas |
|----|---------|--------|-----------|------------|---------|
| RE-01 / CE1 | Preparação e representação | P | alto | wrappers+ontology+smoke | Lot; daily seed |
| RE-02 / CE2 | Cálculo e governança | A | alto | smoke + full cycle | Ramo correção documentar |
| RE-03 / CE3 | Predição e separação | A | médio | forecast page + model 50p | Screenshot Cap. 5 |
| RE-04 / CE4 | Proveniência/evidências/integridade | A | alto | smoke Íntegro; Sepolia SUCCESS; forge | Link proveniência↔tx |
| RE-05 / CE5 | Visualização e auditoria | P | alto | 8 rotas 200; audit 19/20 | Painel colapsado; 8≠12 |
| RE-06 | Matriz Cap. 5 | P | médio | Este arquivo + relatórios | Consolidar na dissertação |

---

## Notas de classificação (critério inferido vs dissertação)

1. **RF020 / CE5:** a dissertação menciona interface ampla (seção 4.5.10); a implementação consolidou **8 rotas** com redirects legados — funções acessíveis, mas contagem divergente → Parcial.
2. **RF019:** atendido no caminho **simulado** exercitado pelo Dash nesta sessão; EVM comprovado por **artefato Sepolia histórico**, não por nova tx.
3. **RN-08:** `evidence_key = keccak256(evidence_package_id)`; `idempotency_key = SHA-256(network_code:package_hash)` — não confundir.
