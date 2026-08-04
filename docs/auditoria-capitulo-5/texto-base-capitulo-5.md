# Texto-base para o Capítulo 5 — Avaliação da arquitetura

**Documento auxiliar.** Linguagem técnica e impessoal. Baseado exclusivamente em evidências da auditoria de 2026-08-03. Sujeito à revisão do pesquisador. Afirmações sem evidência foram omitidas ou marcadas como limitação.

Marcações `[INSERIR FIGURA EVID-…]` referem-se ao plano em `plano-evidencias.md`.

---

## 1. Procedimento de avaliação

A avaliação do terceiro ciclo da arquitetura AgroTrace Carbon foi conduzida por inspeção estática do código autoral, execução de suítes de teste dos serviços, scripts de validação do frontend, exercícios ponta a ponta que criam ciclos novos (sem apagar o conjunto de ciclos pendentes pré-existentes) e verificação de carregamento das interfaces Dash. Scripts destrutivos de reset e a aprovação em massa dos ciclos existentes não foram executados. A ancoragem EVM na rede Sepolia não foi reexecutada; utilizaram-se artefatos de validação interativa já existentes em disco, em conjunto com a ancoragem simulada exercitada no caminho Dash.

Os requisitos oficiais RF001–RF021 e RNF001–RNF012 foram classificados como atendido, parcialmente atendido, não atendido ou não verificável, com distinção explícita entre (i) requisito da dissertação, (ii) critério inferido para torná-lo verificável e (iii) recomendação técnica complementar. As decisões arquiteturais (RN-01–RN-10) e os requisitos de evidência dos cenários CE1–CE5 (RE-01–RE-06) foram avaliados de forma auxiliar para a redação deste capítulo.

Detalhamento operacional: `docs/auditoria-capitulo-5/comandos-e-resultados.md` e `matriz-rastreabilidade.md`.

---

## 2. Ambiente avaliado

- **Sistema:** Windows 10, PowerShell; Python 3.11.9 em ambiente virtual local; pytest 9.0.3; Foundry/Anvil 1.7.1.
- **Entrada da aplicação:** `frontend/main.py` (Dash em `127.0.0.1:8050`).
- **Integração:** chamadas Python diretas via adapters (`frontend/services/*_adapter.py`), sem HTTP entre frontend e serviços no caminho Dash (ADR-001/ADR-002).
- **Persistência observada:** filesystem (`cycles`, `normalized`, `ontology_exports`, `publications`, `evidence_packages`) e SQLite de proveniência e blockchain sob `frontend/data/db/`, além do banco local do blockchain-service.
- **Estado inicial:** 454 ciclos persistidos, com revisões predominantemente pendentes e resultados preliminares; ausência de publicações e de pacotes de evidência no caminho frontend antes dos exercícios ponta a ponta.
- **Limitação de versionamento:** o diretório avaliado não é repositório Git; a identificação da versão analisada baseou-se em inventário de arquivos e em carimbos dos artefatos (incluindo validação Sepolia de 2026-07-31).

---

## 3. Mapeamento da implementação

A arquitetura observada organiza-se em módulos especializados — preservação (`save-file`), wrappers/layouts, ontologia AgroMRV-Lite, cálculo de emissões, treinamento de modelos, proveniência (PROV-DM) e blockchain (pacote, Merkle, providers simulado e EVM) — orquestrados pelo frontend Dash.

A navegação efetiva compreende **oito rotas** (`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`, `/technical-audit`, `/settings`), com redirecionamentos legados (por exemplo, `/final-publication` → `/approval`; diversas rotas técnicas → `/technical-audit`). Essa consolidação diverge de menções a doze telas em material auxiliar, porém preserva as funções previstas por meio de abas e redirects.

A pipeline operacional executa onze etapas (`local_orchestrator` / `PIPELINE_STEP_DEFS`); a apresentação visual utiliza dezoito etapas (`pipeline_display`), com divisória após a publicação final para a fase criptográfica. O desbloqueio do blockchain condiciona-se à publicação final (`APPROVED_RESULT_PUBLISHED` / alias `FINAL_ONTOLOGY_PUBLISHED`).

[INSERIR FIGURA EVID-RF020-01-sidebar-8-rotas]  
**Legenda sugerida:** Navegação do protótipo com as oito rotas gerenciais e de auditoria.

[INSERIR FIGURA EVID-RF020-03-stepper-gate]  
**Legenda sugerida:** Stepper estendido com destaque ao gate pós-publicação.

---

## 4. Atendimento aos requisitos funcionais

### 4.1 Entrada, preparação e representação (RF001–RF007; CE1)

A entrada de dados com associação a propriedade, período e layout encontra-se implementada e foi exercitada no smoke ponta a ponta (RF001). A preservação do bruto com SHA-256 ocorre no ingresso (RF002), porém **não** há API de recuperação do artefato original — classificação parcial. Normalização via `process_file` e layouts `intraday:v1`, `monthly:v1` e `annual:v1` foi coberta por testes e pela pipeline (RF003). Validação e guardas de pipeline impedem avanço indevido ao cálculo (RF004).

A associação a granularidades é **parcial** (RF005): há suporte temporal nos layouts e modelagem organizacional de Property e Animal na ontologia, sem classe `Lot`; o seed avaliado concentrou períodos mensais e o validador temporal registrou falhas (incluindo ausência de ciclos diários esperados). A proveniência registra a trajetória do ciclo, com papéis executor, integrator, reviewer e, após publicação nos exercícios desta auditoria, publisher (RF006). A ontologia de trabalho é populada e exportada, com distinção de caminhos working/published (RF007).

[INSERIR FIGURA EVID-RF001-01-entrada-formulario]  
[INSERIR FIGURA EVID-RF006-01-timeline-proveniencia]

### 4.2 Cálculo e governança (RF008–RF010, RF013–RF016; CE2)

O cálculo preliminar de quatro fontes de emissão, com resultados em estado preliminar e sem publicação automática, foi confirmado pelo estado inicial do ambiente e pelos testes ponta a ponta (RF008). O registro de parâmetros é **parcial** (RF009): metadados de método/versão existem, mas fatores e GWP não estão plenamente recuperáveis no dicionário plano do resultado, e um caso anual falhou na validação de revisão. A correção com nova versão preliminar (RF010) possui API (`request_correction`), porém o histórico de revisões PROV no ambiente base estava vazio e o ramo correção→recálculo não foi demonstrado de forma completa nesta sessão.

A revisão humana, a decisão individual (aprovação/rejeição/correção com justificativa), a aprovação geral condicionada e a publicação na ontologia final acoplada ao fluxo de aprovação foram exercitadas com sucesso no smoke e no ciclo completo (RF013–RF016). A publicação não depende de tela independente: `/final-publication` redireciona para `/approval` (RN-10).

[INSERIR FIGURA EVID-RF008-01-resultado-preliminar]  
[INSERIR FIGURA EVID-RF013-01-fila-revisao]  
[INSERIR FIGURA EVID-RF016-01-publicacao-manifesto]

### 4.3 Predição (RF011; CE3)

O serviço de treinamento restringe dados a resultados aprovados/publicados; a inferência é exposta em `/previsoes`, separada da publicação de resultados calculados (RF011; RN-03). A página de previsões passou no script de validação dedicado.

[INSERIR FIGURA EVID-RF011-01-pagina-previsoes]

### 4.4 Métricas e interfaces (RF012, RF020; CE5)

Indicadores derivados são disponibilizados no painel e na análise geral, com validação positiva dos indicadores do dashboard (RF012). A visualização e a auditoria técnica são **parciais** (RF020): as funções são acessíveis nas oito rotas (HTTP 200 confirmado), porém há divergência em relação a doze telas mencionadas em material de apoio e uma falha residual no painel de ações técnicas colapsado.

[INSERIR FIGURA EVID-RF012-01-dashboard-indicadores]  
[INSERIR FIGURA EVID-RF020-02-technical-audit-abas]

### 4.5 Evidências, ancoragem e verificação (RF017–RF021; CE4)

Após a publicação final, o caminho Dash gerou pacotes de evidência, hashes/Merkle e ancoragem simulada, com verificação íntegra no smoke (RF017–RF018, RF021). O gate impediu evidência/ancoragem antes da publicação no teste de ciclo completo (RF019; RN-07). A ancoragem EVM, a idempotência, a adulteração controlada e a revalidação constam do artefato de validação interativa Sepolia (`interactive_validation_20260731_153031`, status SUCCESS), utilizado como evidência documental **sem** nova transação nesta auditoria. Distingue-se, portanto, o caminho SimulatedAnchorProvider (exercitado pelo Dash) do caminho EvmAnchorProvider (comprovado pelo artefato Sepolia e pelos testes Solidity).

[INSERIR FIGURA EVID-RF019-01-gate-bloqueado]  
[INSERIR FIGURA EVID-RF017-01-pacote-evidencias]  
[INSERIR FIGURA EVID-RF019-03-sepolia-summary]  
[INSERIR FIGURA EVID-RF021-01-verificacao-integro]

---

## 5. Atendimento aos requisitos não funcionais

A rastreabilidade ponta a ponta até a transação é **parcial** (RNF001): a proveniência não espelhou âncoras (`audit_blockchain_anchor = 0` após os exercícios), permanecendo a ancoragem no banco do blockchain-service — coerente com a separação de responsabilidades (RN-04), porém exigindo consulta cruzada. A auditabilidade pela UI é **parcial** (RNF002) devido à falha do painel colapsado, apesar de consultas SQL de proveniência validadas (25 OK).

Manutenibilidade modular (RNF003), integridade criptográfica (RNF004), operabilidade das interfaces (RNF007), extensibilidade por layouts YAML e porta de providers (RNF008), reprodutibilidade da canonicalização `json_canonical_v1` (RNF009) e interoperabilidade por artefatos/ABI sem HTTP no caminho Dash (RNF011) foram considerados atendidos, com graus de confiança indicados na matriz. Explicabilidade (RNF005), consistência semântica quanto a Lot (RNF006), versionamento unificado/ABI (RNF010) e proteção de credenciais em repositório sem Git (RNF012) permaneceram parciais.

---

## 6. Resultados dos testes

Nesta sessão foram obtidos, entre outros: ontology 14 passed; calculation 43; wrappers 41 passed / 3 skipped; model-training 50; traceability 104; frontend 22; save-file 4; blockchain 41 passed (após ignorar teste de schema por ausência de `jsonschema`); forge 9 passed. Os scripts `validate_frontend_pipeline`, `validate_global_filter`, `validate_dashboard_indicators`, `validate_provenance_queries`, `validate_forecast_page`, `validate_ontology_domain_source` e `validate_final_pipeline` passaram. Falharam: `validate_pending_approval_seed` (expectativa de 17 pendências incompatível com o ambiente), `validate_property_filter` (rótulo), `validate_temporal_model`, `validate_calculation_review` (1 caso) e `validate_technical_audit` (1 caso).

O smoke (`run_pipeline_smoke_test.py`) e o ciclo completo (`test_full_emission_cycle.py`) passaram, incluindo a negação do gate blockchain antes da publicação. Os 454 ciclos do backup permaneceram presentes (0 ausentes); foram criados ciclos adicionais pelos exercícios.

---

## 7. Evidências da interface

As oito rotas responderam HTTP 200 com o servidor Dash ativo. O plano detalhado de capturas encontra-se em `plano-evidencias.md`. Recomenda-se priorizar: entrada e hash do bruto; cálculo preliminar; fila e decisão de aprovação; manifesto de publicação; stepper com gate; pacote e verificação; previsões; dashboard; auditoria/timeline; e o summary Sepolia como evidência EVM documental.

---

## 8. Limitações da avaliação

1. Ausência de Git no diretório avaliado.  
2. Sem reexecução on-chain Sepolia e sem Anvil (`PRIVATE_KEY`/`CONTRACT_ADDRESS` vazios).  
3. Dependência `jsonschema` ausente — um teste de schema não executado.  
4. Seed com forte predomínio mensal e sem Lot na ontologia.  
5. GET inicial das rotas Dash confirma shell/carregamento; a prova visual detalhada de cada widget depende das capturas ainda a inserir.  
6. Integração criptográfica demonstra integridade, não veracidade do dado agropecuário (limitação já declarada na dissertação).

---

## 9. Requisitos parcialmente atendidos

| ID | Motivo central |
|----|----------------|
| RF002 | Sem API de recuperação do bruto |
| RF005 | Sem Lot; daily insuficiente no seed |
| RF009 | Fatores/GWP incompletos no resultado plano |
| RF010 | Correção/recálculo pouco evidenciado |
| RF020 | 8 rotas vs 12; painel auditoria colapsado |
| RNF001 | Âncora não espelhada na proveniência |
| RNF002 | 1 FAIL no painel técnico |
| RNF005 | Explicabilidade incompleta |
| RNF006 | Lot ausente |
| RNF010 | Versionamento ABI/mapa incompleto |
| RNF012 | Repo sem Git; varredura de logs não exaustiva |
| RN-02 | Alinhamento fino de estados |
| RE-01 / RE-05 / RE-06 | Lacunas CE1/CE5/matriz final na dissertação |

Nenhum RF/RNF oficial foi classificado como não atendido com base nas evidências desta sessão.

---

## 10. Síntese dos resultados

A arquitetura do terceiro ciclo demonstra, com evidência executada, o ciclo de vida de MRV desde a entrada até a verificação criptográfica no caminho simulado, com gate de publicação final, separação entre proveniência e blockchain, separação entre cálculo e predição, e suporte a ancoragem EVM documentada por artefato Sepolia pré-existente. Dos 49 itens avaliados (RF+RNF+RN+RE), 32 foram atendidos e 17 parcialmente atendidos. As principais lacunas para o fechamento do Capítulo 5 são: recuperação do bruto, cobertura de granularidades (Lot/daily), explicabilidade completa dos parâmetros, alinhamento narrativo das oito telas, vínculo UI entre proveniência e transação, e o pacote de figuras previsto no plano de evidências.

Contagens: ver `matriz-rastreabilidade.md`. Pendências priorizadas: `pendencias.md`.
