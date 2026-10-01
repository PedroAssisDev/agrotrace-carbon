# Evidências de blockchain (ancoragem EVM)

Ponteiros para as evidências de ancoragem em rede EVM. A ancoragem só ocorre após
`FINAL_ONTOLOGY_PUBLISHED` (ver [ADR-003](../../architecture/decisions/ADR-003-approval-publication-and-blockchain-gate.md)).

| Evidência | Local | O que comprova |
|-----------|-------|----------------|
| Guia operacional Sepolia | `agrotrace-carbon-blockchain-service/docs/sepolia_deployment.md` | Procedimento atual de deploy/validação |
| Integração EVM | `agrotrace-carbon-blockchain-service/docs/ethereum_integration.md` | Providers e network codes |
| Changelog de integração EVM | [`IMPLEMENTACAO_ETHEREUM_SEPOLIA.md`](IMPLEMENTACAO_ETHEREUM_SEPOLIA.md) | Histórico da introdução do provider EVM |
| Guia longo (arquivo) | [`../../archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md`](../../archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md) | Material expandido histórico |
| Deployment Sepolia | `agrotrace-carbon-blockchain-service/contracts/deployments/sepolia.json` | Endereço/rede do contrato |
| ABI versionada | `agrotrace-carbon-blockchain-service/app/infrastructure/anchoring/contracts/*.abi.json` | Interface de verificação |
| Validação interativa | `agrotrace-carbon-blockchain-service/docs/validacao_interativa_sepolia.md` | Procedimento manual |

## O que estas evidências não comprovam

- Não comprovam a veracidade do dado agropecuário de origem; comprovam apenas a
  integridade e a ancoragem do artefato publicado (hash/Merkle na cadeia).
- A rede Sepolia pode não ter sido reexecutada na auditoria mais recente; ver
  [`../../limitations.md`](../../limitations.md) e [`../../audits/current/`](../../audits/current/).
