# ADR-002 — Integração modular in-process

## Status

Aceito.

## Contexto

Microsserviços HTTP aumentariam complexidade sem ganho para o MVP acadêmico.

## Decisão

Integração por imports Python e adapters. Sem `requests`/`httpx` entre módulos. SQLite/filesystem locais.

FastAPI do traceability permanece como API opcional do próprio serviço (testes), não como contrato do Dash.

## Consequências

- Bootstrap de `sys.path` e DBs no frontend
- Contratos tipados progressivos; envelopes `dict` ainda presentes em pontos da UI
