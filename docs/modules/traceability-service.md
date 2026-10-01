# Módulo: traceability-service (proveniência)

## Visão geral

Observar e registrar a linhagem/proveniência de todo o ciclo (vocabulário de eventos
canônicos 1–20), do dado bruto até a verificação.

**Posição:** atravessa todas as etapas do orquestrador; não substitui blockchain.

## Responsabilidades

- Registrar eventos canônicos (emissão única por fato)
- Consultas read-only para UI/auditoria

## Não faz

- Não ancora nem gera Merkle final
- Registro de proveniência **≠** ancoragem blockchain

## Contratos com o frontend

- `ProvenanceRecorder`, `get_uow_factory`
- Adapter: `frontend/services/provenance_adapter.py`
- FastAPI `:8080` = **opcional/standalone** (não usado pelo Dash)

## Entradas / saídas / persistência

- Entrada: eventos de etapa do orquestrador
- Persistência: `$AGROTRACE_DATA_ROOT/db/provenance.db` (append-only + outbox)
- Ver [../architecture/append-only-tables.md](../architecture/append-only-tables.md)

## Classificação

| Superfície | Classe |
|------------|--------|
| `ProvenanceRecorder` in-process | Implementado |
| FastAPI HTTP | Preparado (não no caminho Dash) |
| Fallback mock no adapter em erro | Degradação (não happy-path) |

## Testes

`pytest` no serviço; `validate_provenance_queries`.

## Relacionados

- RF006; RNF001, RNF002
- README: `agrotrace-carbon-traceability-service/README.md`
- [../architecture/result-state-model.md](../architecture/result-state-model.md)
- [../architecture/data-lifecycle.md](../architecture/data-lifecycle.md)
