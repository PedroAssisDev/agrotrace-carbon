# Módulo: blockchain-service

## Finalidade

Após a publicação final aprovada, montar o pacote de evidências, calcular hashes/Merkle
Root, ancorar e verificar (etapas 14–19).

## Responsabilidades

- Observar a publicação; construir pacote de evidências; gerar Merkle Root.
- Ancorar (provider) e verificar integridade.

## Não faz

- Não age antes de `FINAL_ONTOLOGY_PUBLISHED` (gate obrigatório).
- Não é log operacional da pipeline. Não gera Merkle de artefatos preliminares.

## Contratos e execução

- Use cases: observe → build evidence → anchor → verify (importáveis diretamente).
- Utilitários: `sha256_hex`, `build_merkle_root`; canonicalização `json_canonical_v1`
  (`canonical_json_service`, fail-closed).
- Providers: `providers_registry` com `SimulatedAnchorProvider` (padrão `local_simulated`)
  e `EvmAnchorProvider` (Anvil/Sepolia) via `BlockchainAnchorProviderPort`.
- Contrato: `contracts/src/CarbonEvidenceRegistry.sol`; ABI versionada em
  `app/infrastructure/anchoring/contracts/*.abi.json`.
- CLI: `python -m app.interfaces.cli`.
- Adapter no frontend: `blockchain_adapter`; verificação: `integrity_view_service`;
  gate: `blockchain_view_service.is_blockchain_unlocked()`.

## Entradas / saídas / persistência

- Entrada: manifesto publicado (hashes/ids; sem payload sensível — minimização on-chain).
- Persistência: `AGROTRACE_DATA_ROOT/db/blockchain_service.db` (`hash_record`,
  `verification_log`, `audit_log` append-only).

## Compatibilidade legada

- Provider `local_simulated` como default (sem chave privada).
- Fallback de ABI sem versão para verificar âncoras antigas — não remover.
- Idempotência: chave `SHA-256(network:hash)`; sobrescrita proibida (testes Forge).

## Limitações conhecidas

- Sepolia não reexecutada na última auditoria; evidência documental
  (ver [../evidence/blockchain/README.md](../evidence/blockchain/README.md)).

## Testes e comandos

- `pytest tests/ -m "not blockchain_local and not sepolia"`; `forge test` em `contracts/`.

## Relacionados

- RF017–RF019, RF021; RNF004, RNF010, RNF011, RNF012.
- ADR: [ADR-003](../architecture/decisions/ADR-003-approval-publication-and-blockchain-gate.md).
- Segurança/integridade: [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md);
  schemas/canonical: `agrotrace-carbon-blockchain-service/schemas/`.
