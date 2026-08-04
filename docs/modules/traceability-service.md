# Módulo: traceability-service (proveniência)

## Finalidade

Observar e registrar a linhagem/proveniência de todo o ciclo (etapas 1–20), do dado bruto
até a verificação.

## Responsabilidades

- Registrar eventos canônicos de proveniência (emissão única por fato).
- Prover consultas de proveniência (somente leitura) para a UI/auditoria.

## Não faz

- Não ancora em blockchain nem substitui o blockchain-service. Registro de proveniência
  **não** é ancoragem.

## Contratos com o frontend

- `ProvenanceRecorder`, `get_uow_factory` e use cases importáveis diretamente.
- Adapter: `frontend/services/provenance_adapter`;
  `provenance_query_service` em modo `ro` (read-only).
- FastAPI do serviço é superfície **opcional** e não é usada pelo caminho Dash.

## Entradas / saídas / persistência

- Entrada: eventos de etapa do orquestrador.
- Persistência: `AGROTRACE_DATA_ROOT/db/provenance.db` — ledger append-only + outbox/estado
  operacional mutável (ver [../architecture/append-only-tables.md](../architecture/append-only-tables.md)).

## Compatibilidade legada

Nomes de eventos misturam canônico/legado, com flag `include_legacy` no orchestrator —
aliases só na leitura; não remover sem mapa de eventos.

## Testes e comandos

- `pytest` no serviço; `validate_provenance_queries`.

## Relacionados

- RF006; RNF001, RNF002.
- Detalhe: `agrotrace-carbon-traceability-service/README.md`, `ARCHITECTURE.md`, `RUNBOOK.md`.
- Eventos e estados: [../architecture/result-state-model.md](../architecture/result-state-model.md).
