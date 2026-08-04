# 06 — Estrutura documental alvo (FASE 1)

Estrutura alinhada aos **módulos realmente existentes**. Pastas vazias sem finalidade **não** serão criadas. Conteúdo duplicado não será copiado só para preencher árvore.

---

## Árvore proposta

```text
README.md

docs/
├── README.md                          # índice por público + status
│
├── architecture/
│   ├── overview.md
│   ├── data-lifecycle.md
│   ├── component-responsibilities.md
│   ├── result-state-model.md
│   ├── storage-and-artifacts.md
│   ├── security-and-integrity.md
│   ├── append-only-tables.md          # detalhe técnico (já existe)
│   └── decisions/
│       ├── README.md
│       ├── ADR-001-....md
│       ├── ADR-002-....md
│       └── ADR-003-....md
│
├── modules/
│   ├── frontend.md
│   ├── save-file.md
│   ├── wrappers-service.md
│   ├── ontology-manager.md
│   ├── calculation-service.md
│   ├── model-training-service.md
│   ├── traceability-service.md
│   └── blockchain-service.md
│
├── development/
│   ├── setup.md
│   ├── configuration.md
│   ├── data-directories.md
│   ├── testing.md
│   ├── validation-scripts.md
│   └── troubleshooting.md
│
├── academic/
│   ├── dissertation-alignment.md
│   ├── requirements.md                # gerado/validado a partir de fonte estruturada
│   ├── requirements-traceability.md
│   ├── evaluation-scenarios.md        # CE1–CE5
│   └── evidence-guide.md
│
├── audits/
│   ├── README.md
│   ├── current/                       # auditoria-pos-implementacao
│   └── archive/
│       └── 2026-08-03-capitulo-5/     # capitulo-5 + final/
│
├── evidence/
│   ├── README.md
│   ├── blockchain/                    # ponteiros p/ Sepolia, deployments
│   └── chapter-5/                     # ponteiros p/ planos de figura
│
├── maintenance/
│   └── project-reorganization/        # estes relatórios 00–18
│
└── archive/
    ├── README.md
    ├── legacy-documentation/          # docs/audit, ops antigos após merge
    ├── superseded-requirements/       # requirements_map.yaml
    └── prompts/                       # PROMPT-AUDITORIA, CURSOR_PROMPT
```

---

## Mapeamento origem → destino

| Origem atual | Destino |
|--------------|---------|
| `docs/architecture/*` | reescrever / renomear conforme nomes alvo |
| `docs/domain/*` | alimentar architecture + modules (não duplicar) |
| `docs/operations/*` | `development/` |
| `docs/audit/*` | mesclar em modules/architecture; resto → archive |
| `docs/testing/test-scenarios.md` | `development/testing.md` + academic se CE |
| `docs/decisions/*` | `docs/architecture/decisions/` |
| `docs/auditoria-pos-implementacao/` | `docs/audits/current/` |
| `docs/auditoria-capitulo-5/` | `docs/audits/archive/2026-08-03-capitulo-5/` |
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` | `archive/` ou `evidence/blockchain/` |
| READMEs de serviço | curtos + link `docs/modules/<mod>.md` |
| Docs técnicos profundos (wrappers layouts, blockchain hash) | permanecem no serviço; module aponta |

---

## README raiz (conteúdo obrigatório)

- Nome acadêmico: arquitetura proposta para MRV agropecuário (nome técnico de pastas preservado).
- Finalidade, módulos (tabela), requisitos mínimos, instalação, config, `python main.py`, regressão completa.
- Aviso dados operacionais / `AGROTRACE_DATA_ROOT`.
- Links: `docs/README.md`, dissertação (quando disponível), licença se houver.
- Sem linguagem promocional.
- Blockchain: default simulado + capacidade EVM (Anvil/Sepolia).

---

## `docs/README.md` — públicos

| Público | Seções |
|---------|--------|
| Visão geral | architecture/overview, lifecycle |
| Desenvolvedor | development/*, modules |
| Pesquisador | academic/* |
| Auditor | audits/current, evidence, security |
| Operador | setup, configuration, data-directories |
| Mantenedor | maintenance/project-reorganization |

Cada entrada: título, finalidade, público, status (`atual` | `gerado` | `histórico`).

---

## Documento canônico por módulo

Cada `docs/modules/*.md` cobre (quando aplicável): finalidade, faz/não faz, estrutura, símbolos, I/O, contratos, deps, adapters, persistência, env (só nomes), fluxo, erros, legado, testes, comandos, limites, RF/RNF/CE, ADRs, schemas, exemplo mínimo.

Identificadores técnicos em inglês; prosa em português.

---

## O que não entra na árvore alvo

- Dados operacionais (`frontend/data/`).
- Duplicar Cap. 5 como documentação “atual”.
- Pastas vazias.
- Segunda cópia dos requisitos com numeração inventada.
