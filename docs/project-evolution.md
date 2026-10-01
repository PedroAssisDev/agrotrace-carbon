# Evolução do projeto

Narrativa baseada em evidências versionadas no repositório (código, ADRs, relatórios de
manutenção e auditorias). Não inventa fases sem suporte documental.

## Estado atual (síntese)

Monorepo Python 3.11+ com **8 projetos** instaláveis (`ecosystem-manifest.json`),
frontend Dash como orquestrador in-process, pipeline de **11 etapas** operacionais,
gate blockchain após publicação final, ancoragem **simulada por padrão** e providers
EVM **preparados**. Documentação canônica sob `docs/`; detalhes por módulo em
`docs/modules/` e nos `README.md` de cada serviço.

## Linha do tempo identificável

### 1. Ciclos acadêmicos e arquitetura proposta

O protótipo é posicionado como **terceiro ciclo** de desenvolvimento da pesquisa MRV
agropecuário ([architecture/overview.md](architecture/overview.md),
[academic/dissertation-alignment.md](academic/dissertation-alignment.md)).

Requisitos oficiais RF001–RF021 / RNF001–RNF012 e cenários CE1–CE5 vivem em
`docs/academic/`.

### 2. Integração modular in-process

Decisões registradas em ADRs:

| ADR | Decisão |
|-----|---------|
| [ADR-001](architecture/decisions/ADR-001-frontend-as-interface-and-orchestrator.md) | Frontend como interface e orquestrador |
| [ADR-002](architecture/decisions/ADR-002-in-process-modular-integration.md) | Integração por import Python (sem HTTP entre módulos) |
| [ADR-003](architecture/decisions/ADR-003-approval-publication-and-blockchain-gate.md) | Gate: blockchain só após `FINAL_ONTOLOGY_PUBLISHED` |

O FastAPI do traceability-service permanece como superfície **opcional/standalone**.

### 3. Reorganização do monorepo

Trilha em `docs/maintenance/project-reorganization/` (**histórico**): inventário,
auditoria Markdown, análise de legado, plano de consolidação documental.

Efeitos observáveis no código atual:

- 8 rotas canônicas (sem camada ativa de redirects legados)
- Documentação indexada por público em `docs/README.md`
- Separação clara modules / architecture / development / academic / audits

### 4. Cleanup final de software (empacotamento 1.0.0)

Relatório consolidado a partir de
`docs/maintenance/final-software-cleanup/` (árvore removida após esta consolidação;
conteúdo preservado aqui):

**Classificação da sessão de cleanup:** `PRONTO COM LIMITAÇÕES DECLARADAS`

Concluído naquela trilha (evidência nos `08-final-status` por módulo e no relatório de
integração):

1. Baseline de regressão e scaffolding de relatórios
2. Correção de falhas funcionais de baseline
3. Empacotamento standalone dos 8 projetos (`pyproject`, `.gitignore`, versão 1.0.0)
4. Remoção da camada ativa de legado (incl. `LEGACY_REDIRECTS` no frontend)
5. Scripts de workspace + `ecosystem-manifest.json`
6. Separação `academic-evidence/` e gerador `software-release/` (`tooling/`)

**Limitações declaradas na época (ainda relevantes quando aplicável):**

- Regressão full vs modo `--quick`
- Evidências Cap. 5 / Sepolia históricas (sem reexecução automática de rede)
- Default de ancoragem permanece `local_simulated`
- LICENSE acadêmica restritiva
- Tags `*-v1.0.0` no manifesto, não criadas automaticamente pelo tooling

#### Status por módulo (cleanup)

| Módulo | Classificação registrada |
|--------|--------------------------|
| frontend | Projeto independente pronto (deps de workspace); 8 rotas; legado ativo removido |
| save-file | Pronto (stdlib; emulated/Embrapa) |
| wrappers-service | Pronto |
| ontology-manager | Pronto; Lot OWL parcial |
| calculation-service | Pronto; alguns validadores de detalhe parciais |
| model-training-service | Pronto; LSTM desabilitada; inferência fora do módulo |
| traceability-service | Pronto; FastAPI opcional |
| blockchain-service | Pronto com limitações (Sepolia histórica; default simulado) |

### 5. Blockchain: simulado → EVM preparado

Evolução documentada em:

- `agrotrace-carbon-blockchain-service/docs/ethereum_integration.md`
- Changelog histórico: [evidence/blockchain/IMPLEMENTACAO_ETHEREUM_SEPOLIA.md](evidence/blockchain/IMPLEMENTACAO_ETHEREUM_SEPOLIA.md)
- Guia operacional: `agrotrace-carbon-blockchain-service/docs/sepolia_deployment.md`

| Rede | Código | Estado operacional |
|------|--------|--------------------|
| `local_simulated` | `SimulatedAnchorProvider` | Default implementado |
| `anvil_local` | `EvmAnchorProvider` | Preparado / testável localmente |
| `ethereum_sepolia` | `EvmAnchorProvider` | Preparado; execução externa sob credenciais |

### 6. Separação previsão × MRV oficial

- Treinamento: `ModelTrainingFacade` (serviço)
- Inferência UI: `frontend/services/forecast_inference/`
- Publicação oficial rejeita payload de predição (`publication_service`)

### 7. Navegação da UI

| Antes (legado) | Agora (código) |
|----------------|----------------|
| Rotas técnicas espalhadas + redirects | 8 rotas; auditoria consolidada em `/technical-audit` |
| `/blockchain` como rota | Aba em `/technical-audit` |
| `LEGACY_REDIRECTS` | Removido — paths antigos não redirecionam |

### 8. Dados de demonstração

Seed canônico atual: `reset_and_seed_pending_cycles.py` (FARM-* + Embrapa P-*/BR-*).
Fluxo alternativo de 3 cenários `PROP-*` permanece em `seed_test_scenarios.py`.

## Artefatos históricos (não são estado atual)

| Local | Uso |
|-------|-----|
| `docs/maintenance/project-reorganization/` | Auditoria da reorganização |
| `docs/audits/archive/` | Auditorias Cap. 5 e anteriores |
| `docs/archive/` | Prompts e material arquivado |
| `academic-evidence/` | Evidências acadêmicas históricas |
| `REVISAO_TECNICA_CALCULOS.md` | Revisão técnica profunda de cálculos |
| Guias Sepolia longos / changelogs | Operação e histórico EVM |

## Ver também

- [limitations.md](limitations.md)
- [architecture/overview.md](architecture/overview.md)
- [audits/README.md](audits/README.md)
