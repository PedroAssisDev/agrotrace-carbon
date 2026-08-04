# 17 — Inventário antes/depois (FASE 2)

## Contagem de arquivos (excluindo gerados/gitignored)

| Momento | Rastreados | Não rastreados | Total |
|---------|-----------|----------------|-------|
| Antes (baseline `c724282`) | 1043 | 11 (relatórios FASE 1) | 1054 |
| Depois (`HEAD`) | 1080 | 0 | 1080 |

`git diff --stat c724282 HEAD`: 95 arquivos alterados, 1408 inserções, 208 remoções.

O aumento líquido (+37 rastreados) corresponde aos documentos novos (arquitetura,
módulos, development, academic, READMEs de índice/arquivo) e dois scripts de suporte; os
11 relatórios da FASE 1 passaram de não rastreados a rastreados no baseline. Nenhum
arquivo foi removido.

## Estrutura de documentação resultante

```text
docs/
├── README.md                # índice por público
├── architecture/            # overview, data-lifecycle, component-responsibilities,
│   ├── decisions/           #   result-state-model, storage-and-artifacts,
│   └── ...                  #   security-and-integrity, append-only-tables, + ADRs
├── modules/                 # 8 documentos canônicos de módulo
├── development/             # setup, configuration, data-directories, testing,
│                            #   validation-scripts, troubleshooting
├── academic/                # alignment, requirements, traceability, scenarios, evidence-guide
├── audit/                   # provenance, approval-and-publication, evidence-and-blockchain
├── domain/                  # calculations, temporal-and-organizational-granularity
├── audits/                  # current/ (atual) + archive/ (histórico)
├── evidence/                # blockchain/
├── archive/                 # prompts/ (histórico)
└── maintenance/             # project-reorganization (FASE 1 + FASE 2)
```

## Dados operacionais

Não versionados e intocados: `AGROTRACE_DATA_ROOT` (ciclos, DBs, ontologias publicadas,
evidências). A regressão usou raiz temporária.
