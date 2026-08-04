# 08 — Plano de exclusão (FASE 1)

**Política:** preferir **arquivar** a apagar. Remoção só com classificação DEAD ou DUPLICATE sem valor acadêmico/histórico, sem uso dinâmico/teste/docs/ferramenta, com reversão Git e registro.

---

## Aprovado para remoção nesta proposta

**Nenhum arquivo.**

Lista de remoção FASE 2 inicial: **vazia**.

---

## Itens que NÃO serão removidos (explícito)

| Item | Motivo |
|------|--------|
| Qualquer arquivo sob `auditoria-*` | ACADEMIC-EVIDENCE / HISTORICAL |
| `requirements_map.yaml` | Arquivar após migrar gerador — não delete cego |
| Artefatos Sepolia / deployments | Evidência |
| Scripts migrate/backfill/profile | UNCERTAIN |
| `mock_data.py`, providers, redirects | ACTIVE / LEGACY-COMPAT |
| Bancos, ciclos, ontologias publicadas, manifests | Segurança operacional |
| Schema `anchor_payload` duplicado | Até diff + consolidação |
| Docs wrappers densos | ACTIVE técnico |

---

## Candidatos futuros (após prova adicional — fora do escopo imediato)

| Candidato | Condição mínima |
|-----------|-----------------|
| Uma das cópias de `anchor_payload.schema.json` | Diff idêntico + todas refs atualizadas + testes OK |
| README cache `.pytest_cache` | Já ignorável; não versionar |
| Duplicata textual 100% idêntica de MD gerado | Só se gerador cobrir e archive guardar snapshot |

Mesmo nesses casos, preferir archive + stub de redirect documental se link externo existir.

---

## Template de registro (FASE 2 → `12-removed-items.md`)

Para cada remoção eventual:

```text
caminho_anterior:
classificação:
justificativa:
evidências:
substituto:
testes_executados:
commit:
```

---

## Conclusão

A “limpeza” da FASE 2 é **reorganização e arquivamento**, não deleção em massa. Isso preserva rastreabilidade acadêmica e evita apagar evidências que parecem legadas.
