# Proveniência

O traceability-service registra o histórico via `ProvenanceRecorder` e Unit of Work (caminho Dash).

A aba SQL da Auditoria Técnica consulta `provenance.db` em modo somente leitura (`SELECT`/`WITH`), com validator, limite de linhas e timeout.

O ciclo JSON guarda um espelho operacional de eventos para a UI; o ledger SQLite é a trilha auditável.
