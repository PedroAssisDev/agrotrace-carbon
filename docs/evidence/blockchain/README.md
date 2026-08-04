# Evidências de blockchain (ancoragem EVM)

Ponteiros para as evidências de ancoragem em rede EVM. A ancoragem só ocorre após
`FINAL_ONTOLOGY_PUBLISHED` (ver [gate de aprovação](../../architecture/decisions/ADR-003-approval-publication-and-blockchain-gate.md)).

| Evidência | Local | O que comprova |
|-----------|-------|----------------|
| Changelog de integração EVM | [`IMPLEMENTACAO_ETHEREUM_SEPOLIA.md`](IMPLEMENTACAO_ETHEREUM_SEPOLIA.md) | Histórico da introdução do provider EVM (Anvil/Sepolia) |
| Deployment Sepolia | `agrotrace-carbon-blockchain-service/contracts/deployments/sepolia.json` | Endereço/rede do contrato publicado |
| ABI versionada | `agrotrace-carbon-blockchain-service/app/infrastructure/anchoring/contracts/*.abi.json` | Interface usada na verificação de âncoras |
| Validação interativa | `agrotrace-carbon-blockchain-service/docs/validacao_interativa_sepolia.md` | Procedimento de validação manual em Sepolia |

## O que estas evidências não comprovam

- Não comprovam a veracidade do dado agropecuário de origem; comprovam apenas a
  integridade e a ancoragem do artefato publicado (hash/Merkle na cadeia).
- A rede Sepolia pode não ter sido reexecutada na auditoria mais recente; verifique
  a limitação declarada em [`../../audits/current/`](../../audits/current/).
