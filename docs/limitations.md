# Limitações e classificação do que está implementado

Documento canônico de honestidade técnica. Afirmações aqui seguem o código
executável, não planos futuros.

## Classificação

| Classe | Significado |
|--------|-------------|
| **Implementado** | Comportamento existente e executável no caminho Dash / scripts oficiais |
| **Simulado** | Representado localmente sem integração externa real |
| **Preparados** | Código e testes existem; exigem config/rede externa ou não entram no fluxo default |
| **Parcial** | Existe, mas incompleto ou dependente de artefatos/cobertura |
| **Planejado / desabilitado** | Mencionado ou stub; não executa no fluxo atual |
| **Ausente** | Não há implementação no repositório |

## Implementado

- Pipeline operacional de **11 etapas** (`cycle_state` + `local_orchestrator`)
- Stepper visual de **18 etapas** (+ `AUDIT_STEP` 19 na timeline)
- UI Dash com **8 rotas** (`router.py` / `sidebar.py`)
- Integração in-process via adapters (`*_adapter.py`); sem HTTP entre módulos
- Preservação de original + SHA-256 (save-file)
- Normalização por layouts (wrappers)
- Ontologia populate/validate/export (ontology-manager)
- Cálculo IPCC/ECOFARM (calculation-service)
- Ledger de proveniência SQLite (`provenance.db`) via `ProvenanceRecorder`
- Aprovação humana + publicação de manifesto (`publication_service`)
- Pacote de evidências, hashes, Merkle Root, verificação
- Gate `FINAL_ONTOLOGY_PUBLISHED` antes de evidência/ancoragem
- Seed demo (`reset_and_seed_pending_cycles.py`) e regressão (`run_full_regression.py`)

Evidência típica: `frontend/scripts/run_pipeline_smoke_test.py`,
`frontend/scripts/test_full_emission_cycle.py`.

## Simulado

- Ancoragem default: provider `local_simulated` / `SimulatedAnchorProvider`
  (`BLOCKCHAIN_DEFAULT_NETWORK_CODE`, tipicamente `local_simulated`)
- Em falha de emit de proveniência, o adapter pode devolver dict com
  `source: "mock"` (degradação registrada, não silent happy-path)

## Preparados (não default)

| Item | Evidência | Condição |
|------|-----------|----------|
| EVM Anvil (`anvil_local`) | `EvmAnchorProvider`, `pytest -m blockchain_local` | Anvil + env |
| EVM Sepolia (`ethereum_sepolia`) | CLI/provider/tests marcados `sepolia` | Credenciais + `RUN_SEPOLIA_TESTS=1` |
| FastAPI provenance `:8080` | `provenance_service/main.py` | Standalone; **não** usado pelo Dash |
| CLI blockchain | `python -m app.interfaces.cli` | Operação fora do orquestrador Dash |

## Parcial

- **Previsões / inferência** (`/previsoes`, `forecast_inference/`): depende de artefatos
  treinados no registry; LSTM não entra
- **Detalhe de cálculo por gás** em alguns validadores (RF008/RF009 parciais na auditoria)
- **Classe `Lot` na OWL**: não modelada (RF005/RNF006 parciais)
- **Proveniência**: em erro de emit, pipeline continua com fallback mock no adapter

## Planejado / desabilitado

- LSTM no model-training (`enable_lstm: false`; skip explícito se ligado)
- Comunicação HTTP entre frontend e serviços da pipeline (rejeitada por ADR-002)

## Ausente

- Docker / Docker Compose
- CI/CD oficial versionado como pipeline canônica do monorepo
- Redirects de rotas legadas (`LEGACY_REDIRECTS` removido; paths antigos não redirecionam)
- Rota dedicada `/blockchain` (conteúdo na aba de `/technical-audit`)

## O que não confundir

| Conceito | Realidade |
|----------|-----------|
| Hash SHA-256 do arquivo bruto | Integridade off-chain (save-file) — **não** é ancoragem |
| Registro de proveniência | Ledger SQLite — **não** é blockchain |
| Ancoragem `local_simulated` | Sintética — **não** é prova on-chain |
| Eventos canônicos 1–20 | Vocabulário/ledger — **não** são 20 funções do orquestrador |

## Ver também

- [architecture/overview.md](architecture/overview.md)
- [architecture/security-and-integrity.md](architecture/security-and-integrity.md)
- [project-evolution.md](project-evolution.md)
- [modules/blockchain-service.md](modules/blockchain-service.md)
