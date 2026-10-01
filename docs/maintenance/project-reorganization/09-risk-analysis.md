# 09 — Análise de riscos (FASE 1)

---

## Riscos bloqueadores

| ID | Risco | Severidade | Mitigação |
|----|-------|------------|-----------|
| R01 | Repositório sem commits | Crítica | Exigir commit-base antes da FASE 2; sem isso, abortar limpeza |
| R02 | Autorização ambígua da FASE 2 | Alta | Exigir frase literal `APROVADO PARA EXECUTAR A FASE 2` |

---

## Riscos de perda acadêmica

| ID | Risco | Severidade | Mitigação |
|----|-------|------------|-----------|
| R03 | Apagar auditoria Cap. 5 / prompts / Sepolia | Crítica | Só ARCHIVE; deletion plan vazio |
| R04 | “Corrigir” relatório histórico | Alta | Cabeçalho histórico; não reescrever resultados |
| R05 | Perder numeração oficial RF | Alta | Fonte = `09-resultados.json`; arquivar YAML divergente após migrar gerador |

---

## Riscos técnicos

| ID | Risco | Severidade | Mitigação |
|----|-------|------------|-----------|
| R06 | Quebrar `generate_audit_reports.py` | Alta | Migrar fonte **antes** de mover YAML; teste do gerador |
| R07 | Paths hardcoded em scripts/tests | Alta | Grep + atualização + regressão |
| R08 | Consolidar schema duplicado incorretamente | Média | Diff; manter path do teste primeiro |
| R09 | Remover UNCERTAIN (migrate_*) | Média | Proibido na FASE 2 inicial |
| R10 | Alterar dados operacionais | Crítica | Não tocar DBs/ciclos; usar `AGROTRACE_DATA_ROOT` temp |
| R11 | Transações Sepolia acidentais | Alta | Não rodar smoke Sepolia live; só Anvil/Forge/local |
| R12 | Expor secrets no Git | Alta | `.gitignore`; `scan_secrets`; não commitar `.env` |

---

## Riscos documentais

| ID | Risco | Severidade | Mitigação |
|----|-------|------------|-----------|
| R13 | Docs atuais ainda com 12 telas / só-simulada | Média | Checklist de reescrita |
| R14 | Duplicar requisitos com IDs novos | Alta | Um gerador; validação de IDs |
| R15 | PDF ausente → drift futuro | Média | Documentar dependência; quando PDF entrar, revalidar |
| R16 | Links quebrados pós-move | Média | Verificador automatizado |

---

## Reversão

| Camada | Mecanismo |
|--------|-----------|
| Git | Branch isolada; revert de commits; sem force-push |
| Dados | Não migrar DBs; isolamento por env |
| Docs | Archive preserva originais movidos (git history) |

Sem commit-base, **não há reversão confiável** → FASE 2 bloqueada (R01).

---

## Riscos aceitos (declarados)

- Sepolia não reexecutada na última auditoria (evidência documental preexistente).
- Dois validate_* falhando na regressão atual (fora do escopo desta reorganização).
- Lot ausente na OWL (lacuna funcional conhecida).

A reorganização **não** deve fingir que esses itens foram resolvidos.
