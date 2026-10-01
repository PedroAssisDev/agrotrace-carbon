# 14 — Documentação criada/reescrita (FASE 2)

## Índices e READMEs

- `README.md` (raiz) — reescrito: curto, não promocional, provider simulado+EVM, 8 rotas.
- `docs/README.md` — índice por público, com coluna de status (atual/gerado/histórico).
- `docs/audits/README.md`, `docs/audits/archive/2026-08-03-capitulo-5/README.md` (cabeçalho histórico).
- `docs/evidence/README.md`, `docs/evidence/blockchain/README.md`.
- `docs/archive/README.md`, `docs/archive/prompts/README.md`.
- `docs/architecture/decisions/README.md`.
- Ponteiros nos 7 READMEs de serviço para `docs/modules/<mod>.md`.

## Arquitetura (reescrita/nova)

- `overview.md`, `data-lifecycle.md`, `component-responsibilities.md`,
  `result-state-model.md`, `storage-and-artifacts.md` (atualizado),
  `security-and-integrity.md` (novo).

## Módulos (novos, canônicos)

- `docs/modules/{frontend, save-file, wrappers-service, ontology-manager,
  calculation-service, model-training-service, traceability-service, blockchain-service}.md`.

## Development (consolidado)

- `setup.md`, `configuration.md`, `data-directories.md` (novo), `testing.md`,
  `validation-scripts.md` (novo), `troubleshooting.md` (novo).

## Academic (novo)

- `dissertation-alignment.md`, `requirements.md`, `requirements-traceability.md`,
  `evaluation-scenarios.md`, `evidence-guide.md`.

## Scripts de suporte

- `frontend/scripts/validate_requirements_ids.py` — guarda a numeração oficial.
- `frontend/scripts/check_markdown_links.py` — verificação de links Markdown.

## Correção pontual

- `docs/audit/evidence-and-blockchain.md` — remove a afirmação "ancoragem simulada (MVP)".
