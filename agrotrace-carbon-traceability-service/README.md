# Traceability Service (proveniência)

Ledger append-only de proveniência do ciclo MRV (eventos canônicos do ciclo completo).

> Documento canônico do monorepo: [../docs/modules/traceability-service.md](../docs/modules/traceability-service.md)

## Uso no protótipo Dash (caminho oficial)

O frontend importa `ProvenanceRecorder` / `get_uow_factory` e use cases de registro
**diretamente** (sem HTTP). Adapter: `frontend/services/provenance_adapter.py`.

Banco padrão no protótipo: `$AGROTRACE_DATA_ROOT/db/provenance.db` (schema criado no
bootstrap do frontend).

O ciclo JSON guarda um espelho operacional de eventos para a UI; o ledger SQLite é a
trilha auditável. A aba SQL da Auditoria Técnica consulta o DB em modo somente leitura.

## O que este serviço não faz

- Não ancora em blockchain
- Não gera Merkle Root de artefatos finais (isso é blockchain-service, após o gate)
- Não substitui o blockchain-service

## API HTTP (opcional / standalone)

O FastAPI em `:8080` (`provenance_service/main.py`) é superfície **standalone**
(testes/integração). O caminho oficial do protótipo Dash **não** depende dela.

Exemplos HTTP: [API_EXAMPLES.md](API_EXAMPLES.md) — não confundir com a integração Dash.

## Documentação adicional

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [RUNBOOK.md](RUNBOOK.md)
- [docs/provenance_service_complete_explanation.md](docs/provenance_service_complete_explanation.md)

## Testes

```bash
pytest
```

No frontend: `validate_provenance_queries`.
