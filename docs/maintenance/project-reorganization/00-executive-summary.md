# 00 — Resumo executivo (FASE 1)

> **Status documental:** `histórico`. Síntese atual da evolução:
> [`../../project-evolution.md`](../../project-evolution.md).

**Data:** 2026-08-04  
**Escopo:** inventário, classificação e plano — sem movimentação nem remoção de arquivos.  
**Status (da época):** FASE 1 concluída; aguarda revisão humana e autorização explícita da FASE 2.

## Veredito

O repositório está funcionalmente organizado em oito módulos reais e um frontend Dash com **oito rotas canônicas** e **nove abas** de auditoria técnica. A documentação está fragmentada: há documentação estável em `docs/`, documentação densa por serviço, e **duas camadas de auditoria Cap. 5** (histórico + pós-implementação). Evidências e docs divergentes devem ser **arquivadas**, não apagadas.

## Contagens (ordem de grandeza)

| Métrica | Valor |
|---------|-------|
| Arquivos no disco (excl. venv/cache/lib) | ~4.900 (maioria gerada / gitignored) |
| Python (`.py`) | ~729 |
| Markdown (`.md`) | ~108 autorais |
| Documentos sob `docs/` | 41 `.md` |
| Rotas canônicas frontend | 8 |
| Abas `/technical-audit` | 9 |
| ADRs | 3 |
| Candidatos DEAD com alta confiança | 0 |
| Candidatos a arquivamento (docs/auditorias) | ~30+ arquivos |
| Commits Git | **0** (bloqueio) |

## Classificação agregada (orientação)

| Classe | Tendência |
|--------|-----------|
| CANONICAL / ACTIVE | Código dos 8 módulos, adapters, schemas/contratos, ADRs, auditoria pós-implementação |
| GENERATED | `frontend/data/**`, OWL exports, artifacts ML, saídas auto de auditoria |
| TEST | Suítes por serviço, Forge, `validate_*` |
| ACADEMIC-EVIDENCE / HISTORICAL | Cap. 5 (Aug 3 + `final/`), prompts, artefatos Sepolia |
| LEGACY-COMPATIBILITY | Redirects, alias `yearly`, providers simulados, ABIs |
| DUPLICATE | Camadas de auditoria; schema `anchor_payload` em dois paths; guias Sepolia |
| DEAD | Nenhum comprovado |
| UNCERTAIN | Scripts migrate/backfill/profile |

## Achados críticos

1. **Git sem commits** — FASE 2 proibida até commit-base.
2. **PDF da dissertação ausente** — RF/RNF/CE oficiais tomados de `docs/auditoria-pos-implementacao/09-resultados.json` (alinhado ao PDF).
3. **`requirements_map.yaml` ativo e divergente** — usado por `frontend/scripts/generate_audit_reports.py`; numeração colide com o PDF.
4. **Documentação desatualizada** — “12 telas”, “só ancoragem simulada”, lista de 7 rotas (falta `/previsoes`).
5. **Auditoria atual** — `docs/auditoria-pos-implementacao/`; Cap. 5 anterior é histórica.

## Estrutura proposta (síntese)

```text
README.md + docs/{architecture, modules, development, academic, audits, evidence, maintenance, archive}
```

Detalhe em `06-target-documentation-structure.md`.

## Bloqueios

| Bloqueio | Efeito |
|----------|--------|
| 0 commits Git | Sem baseline reversível → não limpar |
| Sem frase `APROVADO PARA EXECUTAR A FASE 2` | Não mover/remover |
| Itens UNCERTAIN | Não remover |
| Branch `chore/project-organization` | Não criar sem aprovação |

## Pedido de autorização

Revise os arquivos `01`–`10` deste diretório. Se concordar com o plano de migração e exclusão (conservador):

1. Crie (ou autorize) um **commit-base** no Git.
2. Envie exatamente: **`APROVADO PARA EXECUTAR A FASE 2`**.

Até lá, nenhum arquivo do projeto será movido ou removido além destes relatórios de planejamento.
