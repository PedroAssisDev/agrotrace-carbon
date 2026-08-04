# Agrotrace Carbon Blockchain Service

Serviço independente responsável por observar eventos do `agrotrace-carbon-traceability-service`, montar pacotes de evidência, gerar hashes determinísticos, Merkle Roots e simular ancoragem local no MVP.

## Responsabilidades

- Observar `audit_outbox_event` do serviço de proveniência
- Criar `anchor_request`, `evidence_package` e `evidence_item`
- Gerar payload canônico, `package_hash` e `merkle_root`
- Simular ancoragem em rede `local_simulated`
- Verificar integridade dos pacotes
- Manter banco SQLite próprio

## Limites do MVP

- Sem blockchain real
- Sem smart contract
- Sem alteração do serviço de proveniência
- Sem dados sensíveis completos no payload de ancoragem

## Setup

```bash
pip install -e ".[dev]"
python -m app.interfaces.cli init-db
```

Variáveis de ambiente:

- `BLOCKCHAIN_DATABASE_URL` (default: `./data/blockchain_service.db`)
- `BLOCKCHAIN_PROVENANCE_DATABASE_URL` (default: path para `../agrotrace-carbon-traceability-service/data/provenance.db`)

## Comandos CLI

```bash
python -m app.interfaces.cli observe-events
python -m app.interfaces.cli process-anchor-requests
python -m app.interfaces.cli build-evidence-package --event-id <outbox_event_id>
python -m app.interfaces.cli simulate-anchoring --package-id <evidence_package_id>
python -m app.interfaces.cli verify-package --package-id <evidence_package_id>
python -m app.interfaces.cli reprocess-failed
python -m app.interfaces.cli audit-report --package-id <evidence_package_id>
```

Worker contínuo:

```bash
python scripts/run_worker_loop.py
```

## Testes

```bash
python -m pytest tests/ -q
python -m unittest tests/test_anchor_payload_schema.py
```

## Estrutura

- `app/domain` — entidades, serviços de hash/Merkle, portas
- `app/application` — use cases
- `app/infrastructure` — SQLite, readers de proveniência, provider simulado
- `app/interfaces` — CLI e worker
- `schemas/` — DDL SQLite e JSON Schemas
- `docs/` — documentação técnica

## Documentação

Consulte `docs/architecture.md`, `docs/provenance_integration.md`, `docs/hash_strategy.md` e `docs/mvp_roadmap.md`.
