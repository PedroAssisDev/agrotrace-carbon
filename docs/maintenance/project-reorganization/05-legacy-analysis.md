# 05 — Análise de legado (FASE 1)

Diferencia legado **necessário**, legado **não utilizado** e legado **acadêmico**.

---

## 1. Legado ainda necessário (LEGACY-COMPATIBILITY)

### 1.1 Redirects de rotas

**Onde:** `frontend/pages/router.py` → `LEGACY_REDIRECTS`.

**Comportamento:** URLs antigas (`/blockchain`, `/provenance`, `/final-publication`, …) redirecionam para `/technical-audit`, `/approval` ou `/`.

**Por que manter:** bookmarks, docs antigos, dissertação podem citar rotas históricas.

**Documentar:** tabela legado → canônico no module frontend.  
**Teste:** já coberto indiretamente por navegação; ideal assert de redirect na FASE 2.  
**Descontinuação:** só após Cap. 5 estável e aviso explícito.

### 1.2 Alias temporal `yearly` ↔ `annual`

**Onde:** `domain_catalog`, ontology `cycle_model`, calculation `TemporalScope.YEARLY`, defaults `*_yearly`.

**Canônico de UI/docs:** `daily` | `monthly` | `annual`.  
**`yearly`:** somente leitura/compat.

**Não remover.** Manter testes de normalização.

### 1.3 Filtro global `property_ids` / `period_mode`

**Onde:** `frontend/utils/global_filter.py`.

Leitura legada de `property_ids[0]` quando `farm_id` ausente; `period_mode` deprecated.

### 1.4 Ciclos / lot

`lot_id` opcional; Lot incompleto na OWL (auditoria RF005 parcial). Compat de leitura de ciclos antigos sem lot deve permanecer.

### 1.5 Wrappers `process_file_auto`

Deprecated; ainda no caminho de import fallback. Manter até remoção coordenada com adapters.

### 1.6 Save-file: retrieve por `sha256` vs `artifact_id`

Compat documentada no README do save-file — preservar.

### 1.7 Blockchain: Simulated + ABI sem versão

- Default rede: `local_simulated`.
- ABI versionada + fallback path antigo — necessário para verificação de âncoras antigas.

### 1.8 Nomes de eventos de proveniência

Mistura canônica / legacy com flag `include_legacy` no orchestrator — não remover sem mapa de eventos.

---

## 2. Legado não utilizado (candidatos)

| Item | Veredito FASE 1 |
|------|-----------------|
| Páginas Dash 12-telas como módulos | Já removidas; só redirects |
| Scripts migrate/backfill sem CI | UNCERTAIN — não tratar como morto |
| `requirements_map.yaml` numeração | ACTIVE mas **superado semanticamente** → arquivar após migrar gerador |

Nenhum “legado morto” comprovado para exclusão nesta fase.

---

## 3. Legado acadêmico (arquivar, não apagar)

| Artefato | Valor |
|----------|-------|
| `auditoria-capitulo-5/` completa | Rastreabilidade Cap. 5 Aug 3–4 AM |
| Prompt de auditoria Cursor | Metodologia reproduzível |
| Texto-base Cap. 5 | Redação dissertação |
| Artefatos Sepolia / deployment JSON | Evidência EVM sem reexecutar rede |
| Relatórios model-training (`ANALYSIS_*`, `VALIDATION_*`) | Evidência ML |
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` | Histórico de introdução EVM |

Cabeçalho sugerido ao arquivar:

```markdown
> **Status:** histórico  
> **Substituído por:** …  
> **Data do conteúdo:** AAAA-MM-DD  
> Preservado para rastreabilidade; não representa o estado atual.
```

---

## 4. Divergências documentais a corrigir (não são “código legado”)

| Divergência | Correção |
|-------------|----------|
| 12 telas vs 8 rotas + 9 abas | Docs atuais + `.cursor/rules` |
| Blockchain só simulada | Default simulado + provider EVM |
| YAML RF vs PDF | Fonte = `09-resultados.json` |
| Docs ops com 7 rotas | Incluir `/previsoes` |

---

## 5. Condição de descontinuação (futuro)

Só descontinuar compat após:

1. Cap. 5 dissertação estável com numeração e rotas oficiais;
2. Migração de dados antigos concluída;
3. Testes de compat marcados e depois removidos com ADR;
4. Aviso em CHANGELOG/academic.

Até lá: **preservar + documentar + testar**.
