# Módulo: blockchain-service

## Visão geral

Após a publicação final aprovada, montar o pacote de evidências, calcular hashes/Merkle
Root, ancorar e verificar. No stepper visual corresponde às etapas 14–18 (orquestrador
9–11: `evidence` / `blockchain` / `verification`).

## Responsabilidades

- Observar a publicação; construir pacote; gerar Merkle Root
- Ancorar (provider) e verificar integridade

## Não faz

- Não age antes de `FINAL_ONTOLOGY_PUBLISHED`
- Não é log operacional da pipeline
- Não gera Merkle de artefatos preliminares

## Contratos e execução

| Peça | Onde |
|------|------|
| Use cases | observe → build → anchor → verify |
| Canonicalização | `json_canonical_v1` (fail-closed) |
| Providers | `local_simulated`, `anvil_local`, `ethereum_sepolia` |
| Contrato | `contracts/src/CarbonEvidenceRegistry.sol` |
| CLI | `python -m app.interfaces.cli` |
| Adapter FE | `blockchain_adapter.py` |
| Gate UI | `blockchain_view_service.is_blockchain_unlocked()` |

Implementado em: `agrotrace-carbon-blockchain-service/app/application/use_cases/`.

## Entradas / saídas / persistência

- Entrada: manifesto publicado (hashes/ids; minimização on-chain)
- Persistência: `$AGROTRACE_DATA_ROOT/db/blockchain_service.db` +
  `$AGROTRACE_DATA_ROOT/evidence_packages/`

## Classificação

| Provider | Classe |
|----------|--------|
| `local_simulated` | Implementado (default) |
| `anvil_local` | Preparado |
| `ethereum_sepolia` | Preparado (evidências Cap. 5 históricas) |

## Testes

```bash
pytest tests/ -m "not blockchain_local and not sepolia"
forge test  # em contracts/
```

## Relacionados

- RF017–RF019, RF021; RNF004, RNF010–RNF012
- [ADR-003](../architecture/decisions/ADR-003-approval-publication-and-blockchain-gate.md)
- [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md)
- [../limitations.md](../limitations.md)
- README: `agrotrace-carbon-blockchain-service/README.md`
