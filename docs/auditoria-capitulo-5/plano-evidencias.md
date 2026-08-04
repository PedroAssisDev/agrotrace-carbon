# Plano de evidências (screenshots e artefatos) — Capítulo 5

**Data:** 2026-08-03  
**Convenção de arquivo:** `EVID-<ID>-<NN>-descricao-curta.png`  
**Perfil:** usuário responsável (único ator formal da dissertação)  
**PII:** ocultar caminhos absolutos de usuário, chaves privadas, tokens RPC; hashes e endereços públicos on-chain podem permanecer.

Regras: screenshot de UI **não** prova sozinha regra interna/persistência/segurança; trecho de código **não** substitui demonstração de comportamento na UI. Preferir sequência: (1) estado inicial → (2) ação → (3) resultado → (4) confirmação/persistência.

Pré-condição geral recomendada para sessões visuais: ambiente com (a) ciclos pendentes (já existentes) e (b) pelo menos um ciclo publicado com pacote (gerado pelo smoke desta auditoria, ex.: manifests em `frontend/data/publications/`).

---

## CE1 / Preparação (RF001–RF007)

### EVID-RF001-01-entrada-formulario
- **Requisito:** RF001
- **Rota:** `/data-entry`
- **Pré:** app em `http://127.0.0.1:8050`; filtro global opcional
- **Ações:** abrir Entrada de Dados; exibir campos propriedade, período, layout, upload
- **Estado UI:** formulário visível, sem erro
- **Destacar:** campos de contexto mínimo
- **Comprova:** UI de entrada existe e exige contexto
- **Não comprova:** persistência bem-sucedida (usar EVID-RF001-02)
- **Legenda sugerida:** “Tela de entrada de dados agropecuários com associação a propriedade, período e layout.”

### EVID-RF001-02-ciclo-criado
- **Requisito:** RF001, RF002
- **Rota:** `/data-entry` ou `/technical-audit`
- **Ações:** após upload (ou selecionar ciclo recente do smoke)
- **Destacar:** `cycle_id`, propriedade, período, hash SHA-256 do bruto
- **Comprova:** ciclo associado ao contexto; hash gerado
- **Não comprova:** retrieve API (inexistente — lacuna RF002)

### EVID-RF003-01-lote-normalizado
- **Requisito:** RF003
- **Rota:** `/technical-audit` (aba artefatos / dados) ou detalhe do ciclo
- **Destacar:** layout_id (`monthly:v1` / `intraday:v1` / `annual:v1`), linhas normalizadas
- **Comprova:** normalização aplicada
- **Artefato não visual:** trecho de `frontend/data/normalized/<cycle>.json` sanitizado

### EVID-RF005-01-granularidade-mensal
- **Requisito:** RF005
- **Rota:** `/indicators` ou `/` com fazenda mensal
- **Destacar:** série temporal mensal
- **Comprova:** granularidade monthly operacional
- **Não comprova:** Lot / daily completo (lacunas)

### EVID-RF005-02-ontologia-property-animal
- **Requisito:** RF007, RF005
- **Rota:** `/technical-audit` (ontologia) ou export
- **Artefato:** classes Property/Animal; ausência de Lot documentada
- **Comprova:** representação semântica de trabalho
- **Não comprova:** Lot

### EVID-RF006-01-timeline-proveniencia
- **Requisito:** RF006, RNF002
- **Rota:** `/technical-audit` aba timeline/proveniência
- **Pré:** ciclo com eventos (pendente ou publicado)
- **Destacar:** sequência RAW → WRAPPER → … → (APPROVED/PUBLISHED se houver)
- **Comprova:** linhagem consultável na UI
- **Complemento:** EVID-RF006-02 consulta SQL template (aba consultas) — validate_provenance_queries já OK

---

## CE2 / Cálculo e governança (RF008–RF010, RF013–RF016)

### EVID-RF008-01-resultado-preliminar
- **Requisito:** RF008
- **Rota:** `/calculations`
- **Pré:** ciclo pending approval
- **Destacar:** badge/estado preliminar; CO2e; fontes
- **Comprova:** cálculo preliminar sem publicação automática
- **Não comprova:** parâmetros completos (RF009 parcial)

### EVID-RF009-01-parametros-metodo
- **Requisito:** RF009, RNF005
- **Rota:** `/calculations` detalhe / `/approval` item
- **Destacar:** method_code/version; fatores visíveis se houver
- **Comprova:** parte dos parâmetros
- **Não comprova:** GWP/fatores no flat dict (lacuna)

### EVID-RF013-01-fila-revisao
- **Requisito:** RF013
- **Rota:** `/approval`
- **Pré:** ciclos pendentes (ambiente atual)
- **Destacar:** lista de itens AWAITING_REVIEW / pending
- **Comprova:** revisão humana iniciável

### EVID-RF014-01-aprovacao-item
- **Sequência:** (1) item pendente (2) ação aprovar/rejeitar com justificativa (3) status atualizado (4) evento na timeline
- **Requisito:** RF014
- **Rota:** `/approval`

### EVID-RF015-01-finalize-bloqueado
- **Requisito:** RF015
- **Pré:** pelo menos um item pendente
- **Destacar:** `can_finalize` negado / botão bloqueado
- **Comprova:** aprovação geral bloqueada

### EVID-RF015-02-finalize-liberado
- **Pré:** todos obrigatórios decididos/aprovados
- **Destacar:** finalize habilitado

### EVID-RF016-01-publicacao-manifesto
- **Requisito:** RF016, RN-10
- **Rota:** `/approval` (não `/final-publication` — redirect)
- **Destacar:** manifesto / publication_hash / ontology final path
- **Artefato:** `frontend/data/publications/CYCLE-*_*.json`
- **Comprova:** publicação vinculada à aprovação
- **Não comprova:** ancoragem (RF019)

### EVID-RF010-01-correcao-recalculo
- **Requisito:** RF010
- **Status roteiro:** **pendente de execução dedicada** (lacuna P-M01)
- **Ações desejadas:** solicitar correção → ajustar fator → recálculo → nova versão preliminar na timeline

---

## CE3 / Predição (RF011, RN-03)

### EVID-RF011-01-pagina-previsoes
- **Rota:** `/previsoes`
- **Destacar:** área de estimativas separada de cálculos publicados
- **Comprova:** separação visual cálculo × predição
- **Não comprova:** que forecast nunca entra no OWL final (precisa assert/teste)

### EVID-RF011-02-treino-aprovados
- **Artefato não visual:** configuração/`normalize_approved_results` + saída model-training
- **Comprova:** treino filtra approved/published

---

## CE4 / Evidências e integridade (RF017–RF021, RNF004)

### EVID-RF017-01-pacote-evidencias
- **Rota:** `/technical-audit` aba blockchain/evidências
- **Pré:** ciclo com `is_blockchain_unlocked`
- **Destacar:** package_hash, merkle_root, itens
- **Artefato:** `frontend/data/evidence_packages/*`

### EVID-RF018-01-hashes-merkle
- **Destacar:** package_hash + merkle_root recalculáveis
- **Complemento:** saída unit tests hash/merkle; smoke “VERIFICADO / ÍNTEGRO”

### EVID-RF019-01-gate-bloqueado
- **Requisito:** RF019, RN-07
- **Pré:** ciclo preliminar/approved sem publication
- **Destacar:** blockchain locked / mensagem WAITING_FINAL_PUBLICATION
- **Comprova:** gate antes da publicação
- **Evidência de teste:** full cycle `BLOCKCHAIN_LOCKED`

### EVID-RF019-02-ancoragem-simulada
- **Pré:** ciclo publicado do smoke
- **Destacar:** tx simulada / status anchored
- **Comprova:** ancoragem SimulatedAnchorProvider no caminho Dash
- **Não comprova:** EVM Sepolia

### EVID-RF019-03-sepolia-summary
- **Tipo:** artefato JSON (não screenshot de código como prova única)
- **Arquivo fonte:** `agrotrace-carbon-blockchain-service/evidence/sepolia/interactive_validation_20260731_153031/summary.json`
- **Destacar:** status PASSOU; chain_id 11155111; contract; tx hash; block 11390296
- **Comprova:** CE4 EVM histórico (idempotência, adulteração, revalidação)
- **Não comprova:** fluxo Dash→Sepolia nesta sessão
- **Nome sugerido:** `EVID-RF019-03-sepolia-validation-summary.png` (print do summary sanitizado) ou anexar JSON

### EVID-RF021-01-verificacao-integro
- **Rota:** auditoria / integridade
- **Destacar:** correspondência local (e on-chain se EVM)
- **Comprova:** RF021 caminho simulado

### EVID-RF021-02-adulteracao-divergencia
- **Fonte preferencial:** artefato Sepolia `Adulteração` / `Revalidação original` = PASSOU
- **Alternativa:** demo `intentional_tamper_demo` na UI se disponível
- **Comprova:** divergência sem alterar registro na rede

---

## CE5 / Operabilidade (RF012, RF020, RNF007)

### EVID-RF012-01-dashboard-indicadores
- **Rotas:** `/` e `/indicators`
- **Destacar:** CO2e, intensidade, evolução, governança
- **Comprova:** métricas derivadas na UI

### EVID-RF020-01-sidebar-8-rotas
- **Destacar:** 8 itens de navegação
- **Comprova:** interface consolidada
- **Nota dissertação:** explicar consolidação vs 12 telas antigas / redirects

### EVID-RF020-02-technical-audit-abas
- **Rota:** `/technical-audit`
- **Destacar:** 9 abas (resumo, timeline, proveniência, SQL, artefatos, blockchain, integridade, logs, payload)
- **Lacuna:** capturar após corrigir TechnicalActionsPanel (P-A04)

### EVID-RF020-03-stepper-gate
- **Componente:** ExtendedPipelineStepper
- **Destacar:** divisória pós-publicação / etapas blockchain
- **Comprova:** visualização do gate RN-07

---

## Evidências não visuais (obrigatórias no Cap. 5)

| ID | Tipo | Fonte | Requisitos |
|----|------|-------|------------|
| EVID-CMD-01 | log sanitizado | `comandos-e-resultados.md` | RE-06 |
| EVID-TEST-01 | pytest summary | 328 passed nesta sessão | vários |
| EVID-FORGE-01 | `forge test` 9 PASS | contracts | RN-08, RF019 |
| EVID-SMOKE-01 | saída Smoke OK | e2e | CE2/CE4 |
| EVID-GATE-01 | BLOCKCHAIN_LOCKED | full cycle | RN-07 |
| EVID-DB-01 | inventário before/after | `_inventory_before.json` + após | RE-06 |
| EVID-SEP-01 | summary.json Sepolia | evidence/sepolia/... | CE4 |
| EVID-KEYS-01 | diagrama evidence_key vs idempotency_key | RN-08 | RN-08 |

---

## Ordem sugerida de captura (sessão única)

1. Sidebar 8 rotas (RF020-01)
2. Entrada + ciclo com hash (RF001/002)
3. Cálculos preliminar (RF008)
4. Aprovação: fila → item → finalize bloqueado/liberado (RF013–015)
5. Manifesto publicação (RF016)
6. Stepper com gate (RF020-03)
7. Pacote + verify íntegro (RF017/021)
8. Gate bloqueado em outro ciclo pendente (RF019-01)
9. Previsões (RF011)
10. Dashboard/indicadores (RF012)
11. Auditoria timeline + SQL (RF006)
12. Anexar Sepolia summary (RF019-03)

**Estimativa:** ~20–25 imagens + 8 artefatos não visuais.
