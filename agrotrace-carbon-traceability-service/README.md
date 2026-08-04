# Traceability Service (proveniência)

Ledger append-only de proveniência do ciclo MRV.

> Documento canônico do módulo: [../docs/modules/traceability-service.md](../docs/modules/traceability-service.md).

## Uso no protótipo Dash

O frontend consome o pacote Python `provenance_service` via Unit of Work / `ProvenanceRecorder` (chamada direta). O banco padrão no protótipo fica em `frontend/data/db/provenance.db`.

## API HTTP (opcional)

O FastAPI em `:8080` é superfície **standalone** do próprio serviço (testes/integração). O caminho oficial do protótipo Dash **não** depende dela.

## Testes

Ver suíte em `tests/` deste pacote e o smoke do frontend.
