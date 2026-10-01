# Segurança e integridade

Mecanismos de integridade criptográfica e proteção de credenciais do protótipo. A
profundidade técnica vive no blockchain-service; este documento consolida os conceitos e
seus limites.

## Cadeia de integridade

| Mecanismo | Papel | Referência |
|-----------|-------|------------|
| Canonicalização | Serialização determinística antes de hash | `agrotrace-carbon-blockchain-service/schemas/canonical/canonicalization_rules.md` |
| SHA-256 | Hash de conteúdo de artefatos (itens, pacote) | `agrotrace-carbon-blockchain-service/docs/hash_strategy.md` |
| Merkle Root | Agregação verificável dos itens do pacote | `agrotrace-carbon-blockchain-service/docs/merkle_strategy.md` |
| Keccak-256 | Hash usado na camada EVM (compatibilidade Ethereum) | `agrotrace-carbon-blockchain-service/docs/ethereum_integration.md` |

## Minimização on-chain

A âncora registra apenas hashes/ids do manifesto (Merkle Root e identificadores), sem
payload sensível completo. Dados agropecuários e pessoais não vão para a cadeia.

## Gates e política append-only

- Nenhuma ação de blockchain antes de `FINAL_ONTOLOGY_PUBLISHED`
  ([ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md)).
- Tabelas de ledger (proveniência) e `hash_record` / `verification_log` / `audit_log`
  (blockchain) são append-only — ver [append-only-tables.md](append-only-tables.md).

## Proteção de credenciais

- Segredos nunca são versionados; `.env` é ignorado pelo Git (`.env.example` só contém
  placeholders fictícios).
- Provider `local_simulated` (padrão) **não** exige chave privada.
- Providers EVM (Anvil/Sepolia) leem chaves apenas do `.env` local.
- Varredura automática: `frontend/scripts/scan_secrets.py` (RNF012) — não imprime valores.
- Detalhe: `agrotrace-carbon-blockchain-service/docs/security_and_secrets.md`.

## Limites da integridade criptográfica

A integridade prova que um artefato **não foi alterado** após a publicação e que a âncora
corresponde ao Merkle Root registrado. Ela **não** comprova a veracidade do dado
agropecuário de origem, nem a correção do cálculo de emissões. Veracidade e adequação
metodológica são questões separadas, tratadas na revisão humana e na dissertação.
