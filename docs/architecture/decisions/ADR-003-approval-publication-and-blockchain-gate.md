# ADR-003 — Aprovação, publicação e gate blockchain

## Status

Aceito.

## Contexto

Dados preliminares não devem ser ancorados.

## Decisão

1. Cálculos são preliminares até revisão/aprovação.
2. Publicação gera manifesto imutável com hash canônico.
3. Blockchain (evidência/Merkle/âncora/verify) só após `APPROVED_RESULT_PUBLISHED`.
4. Blockchain não altera dados de negócio.

## Consequências

- Gate em `blockchain_view_service` / `pipeline_guards`
- Pacote de evidências baseado no manifesto, não em planilhas completas
