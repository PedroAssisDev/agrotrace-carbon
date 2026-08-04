# 12 — Itens removidos (FASE 2)

## Arquivos removidos

**Nenhum.** O [08-deletion-plan.md](08-deletion-plan.md) não aprovou remoções: a política
foi arquivar em vez de apagar, preservando a rastreabilidade acadêmica. Nenhum arquivo
foi excluído do repositório.

## Conteúdo removido (não-arquivo)

Foram removidas apenas linhas de links órfãos pré-existentes (não introduzidos por esta
reorganização), para restaurar a validade dos links:

| Arquivo | Linhas removidas |
|---------|------------------|
| `agrotrace-carbon-wrappers-service/README.md` | 3 links para docs consolidados inexistentes (`00_/01_/02_ARQUITETURA_*`) |
| `agrotrace-carbon-wrappers-service/docs/README.md` | 2 links para runbooks inexistentes (`runbooks/kubernetes.md`, `runbooks/message-queues.md`) |

Justificativa: apontavam para arquivos que não existem no repositório; substituídos por
ponteiro ao documento canônico ou removidos. Reversível via Git.

## Commit responsável

`c10216c`.
