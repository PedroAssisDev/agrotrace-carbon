# Guia de evidências (Capítulo 5)

Orienta quais evidências pertencem ao Capítulo 5, como gerá-las, como sanitizá-las e o
que cada uma comprova (e o que não comprova). O plano detalhado da auditoria está em
[../audits/current/08-plano-evidencias-capitulo-5.md](../audits/current/08-plano-evidencias-capitulo-5.md).

## Evidências e como gerar

| Evidência | Como gerar | Comprova |
|-----------|-----------|----------|
| Regressão completa (JSON) | `python frontend/scripts/run_full_regression.py` | Execução de testes/validações em ambiente isolado |
| Matriz de requisitos | Auditoria em `docs/audits/current/` (gerada por `_gen_reports.py`) | Cobertura RF/RNF/CE observada |
| Ciclo completo + gate | `python frontend/scripts/test_full_emission_cycle.py` | Fluxo até ancoragem e verificação |
| Integridade | `validate_reproducibility` | Hash/Merkle estáveis; detecção de adulteração |
| Ancoragem EVM | `contracts/` (Forge) e deployment Sepolia | Contrato e âncora (ver [evidência blockchain](../evidence/blockchain/README.md)) |

## Como sanitizar

- Nunca inclua chaves privadas, URLs com token ou `.env` real.
- Rode `python frontend/scripts/scan_secrets.py` antes de anexar artefatos.
- Substitua caminhos pessoais por caminhos relativos/genéricos.
- Trunque hashes longos apenas em prosa; preserve os valores completos nos artefatos.

## O que as evidências não comprovam

- Integridade criptográfica **não** comprova a veracidade do dado agropecuário nem a
  correção metodológica do cálculo (ver
  [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md)).
- Uma auditoria em que a Sepolia não foi reexecutada não comprova execução ao vivo na
  rede; a evidência é documental.
