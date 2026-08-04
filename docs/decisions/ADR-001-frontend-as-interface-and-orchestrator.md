# ADR-001 — Frontend como interface e orquestrador

## Status

Aceito (protótipo acadêmico).

## Contexto

É necessário demonstrar a pipeline MRV completa com UI auditável.

## Decisão

O frontend Dash é interface **e** orquestrador in-process (`local_orchestrator`). Não é “apenas camada visual”.

## Consequências

- Simplicidade de execução (um processo)
- Acoplamento consciente aos módulos via adapters
- Fórmulas, Merkle e ontologia permanecem nos módulos especializados
