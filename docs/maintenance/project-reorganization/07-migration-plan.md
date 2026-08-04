# 07 — Plano de migração FASE 2 (proposto)

**Pré-condições obrigatórias**

1. Commit-base Git existente (revertível).
2. Mensagem explícita: `APROVADO PARA EXECUTAR A FASE 2`.
3. Branch dedicada (ex.: `chore/project-organization`) — criar **só** com autorização.
4. Working tree inspecionada; sem secrets em arquivos a versionar.

**Não fazer na FASE 2:** reset destrutivo sem confirmação; exclusão de DBs/ciclos/ontologias/evidências Sepolia; txs externas; mudança funcional estética.

---

## Ordem de execução

### Passo 0 — Baseline

- Registrar `git status`, `git log -1`, inventário (reutilizar/atualizar `01`).
- Confirmar branch.
- Varredura `scan_secrets.py` (somente leitura).

### Passo 1 — Estrutura de pastas

Criar apenas diretórios que receberão conteúdo imediato (`architecture/decisions`, `modules`, `development`, `academic`, `audits/{current,archive/...}`, `evidence`, `archive/...`).

### Passo 2 — Auditorias

| De | Para |
|----|------|
| `docs/auditoria-pos-implementacao/**` | `docs/audits/current/` |
| `docs/auditoria-capitulo-5/**` | `docs/audits/archive/2026-08-03-capitulo-5/` |

Adicionar README em cada archive (data, versão, status histórico, sucessor).

### Passo 3 — Requirements map

1. Extrair fonte alinhada (`09-resultados.json` / matriz).
2. Atualizar `generate_audit_reports.py` para nova fonte.
3. Adicionar validação de IDs RF001–RF021 / RNF001–RNF012 / CE1–CE5.
4. Mover `requirements_map.yaml` → `docs/archive/superseded-requirements/` com cabeçalho histórico.

### Passo 4 — ADRs e architecture

- Mover ADRs → `docs/architecture/decisions/`.
- Reescrever overview, data-lifecycle, component-responsibilities, result-state-model, storage, security.
- Mapear conteúdo de `domain/` e `audit/` sem duplicar prosa.

### Passo 5 — Modules + development + academic

- Criar 8 docs de módulo a partir do código atual.
- Mover/reescrever ops → development.
- Gerar `academic/requirements.md` e traceability/CE/evidence-guide.

### Passo 6 — Raiz e índices

- Reescrever `README.md` (curto).
- Reescrever `docs/README.md` (mapa por público).
- Mover `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` para archive/evidence.
- Atualizar READMEs de serviço (links relativos).

### Passo 7 — Prompts e stray

- `PROMPT-AUDITORIA-CURSOR.md`, `CURSOR_PROMPT.md` → `docs/archive/prompts/`.
- Relatórios ML → archive ou evidence conforme `03`.

### Passo 8 — Links e paths

- Grep por caminhos antigos (`auditoria-capitulo-5`, `docs/decisions`, `conceptual_model_mrv`, etc.).
- Atualizar Python/YAML/MD/rules Cursor.
- Introduzir verificador de links Markdown.
- Executar verificação.

### Passo 9 — Remoções

- Aplicar **somente** itens de `08-deletion-plan.md` (lista conservadora).
- Registrar em `12-removed-items.md`.

### Passo 10 — Compatibilidade

- Comentários/docs em redirects, yearly, providers.
- Garantir testes de alias/redirects passam.

### Passo 11 — Regressão

Conforme `10-validation-plan.md` (ambiente isolado `AGROTRACE_DATA_ROOT`).

### Passo 12 — Relatórios finais

Produzir `11`–`18` neste diretório.

---

## Atualização de referências conhecidas

| Referência antiga | Nova |
|-------------------|------|
| `docs/auditoria-pos-implementacao/` | `docs/audits/current/` |
| `docs/auditoria-capitulo-5/` | `docs/audits/archive/2026-08-03-capitulo-5/` |
| `docs/decisions/` | `docs/architecture/decisions/` |
| `docs/auditoria-capitulo-5/requirements_map.yaml` | archive + nova fonte no gerador |
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` | sob `docs/archive` ou `docs/evidence/blockchain` |

---

## Critério de parada / rollback

Qualquer falha de regressão crítica ou perda de evidência acadêmica → reverter commit(s) da branch; não forçar merge.
