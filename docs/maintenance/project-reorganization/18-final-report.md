# 18 — Relatório final (FASE 2)

## Resultado

Reorganização executada na branch `chore/project-organization`, em commits pequenos e
reversíveis (ver [11-migration-executed.md](11-migration-executed.md)). Nenhum arquivo
removido; movimentações via `git mv` com histórico preservado; nenhum dado operacional
tocado; sem transações externas.

## Objetivos atendidos

- Raiz enxuta: `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` movido para `docs/evidence/blockchain/`.
- README raiz curto e não promocional; índice `docs/README.md` por público.
- Documento canônico por módulo (`docs/modules/`, 8 módulos).
- Arquitetura reescrita e alinhada (8 rotas, provider simulado+EVM).
- Auditoria atual separada da histórica (`docs/audits/current` vs `docs/audits/archive`).
- Documentos históricos com cabeçalho (data, versão, status, sucessor).
- Requisitos com numeração oficial (RF001–RF021, RNF001–RNF012, CE1–CE5) +
  validação automática de IDs.
- Rotas e funções do frontend conferidas contra `router.py`.
- Links válidos (`broken_count=0`); ver [15-links-validation.md](15-links-validation.md).
- Sem segredos/caminhos pessoais na documentação canônica.

## Correção de fato relatada na FASE 1

Os relatórios da FASE 1 registraram "0 commits / branch `master`" como bloqueio (R01). Na
prática o repositório já tinha histórico e a FASE 2 rodou na branch
`chore/project-organization` a partir de `dev`. O bloqueio R01 não se aplica; os relatórios
FASE 1 foram preservados como planejamento e esta correção fica registrada aqui.

## Desvios conscientes do plano

- `docs/audit/{provenance, approval-and-publication, evidence-and-blockchain}.md` foram
  mantidos como notas de tópico (apontados pelos módulos) em vez de fundidos/arquivados,
  para reduzir churn; `evidence-and-blockchain.md` foi corrigido (sem "MVP simulada").
- `requirements_map.yaml` foi arquivado junto de sua auditoria histórica
  (`docs/audits/archive/2026-08-03-capitulo-5/`) em vez de uma pasta
  `superseded-requirements/` separada, evitando duplicação; o gerador histórico
  `generate_audit_reports.py` foi repontado para o archive.
- `docs/domain/{calculations, temporal-and-organizational-granularity}.md` permanecem como
  fonte canônica de domínio (referenciados pelos módulos), sem duplicar conteúdo.

## Pendências (não resolvidas por esta reorganização)

- Relatórios `PROJECT_SPEC`/`ANALYSIS_REPORT`/`VALIDATION_REPORT` do model-training
  permanecem no serviço (não arquivados); avaliar em passo futuro.
- Limitações técnicas declaradas na auditoria seguem abertas: classe `Lot` na OWL;
  dois `validate_*` de cálculo/detalhe; Sepolia não reexecutada (evidência documental).
- PDF/LaTeX da dissertação não versionado; revalidar requisitos quando entrar no repo.

## Regressão

Ver [16-tests-and-regression.md](16-tests-and-regression.md).

Resumo: **39 PASS / 2 FAIL** sob `AGROTRACE_DATA_ROOT` temporário. Falhas:
`validate_emulated_import` e `validate_preliminary_calculation_form` (funcionais
pré-existentes; não causadas pela reorganização documental). Smoke, full emission
cycle, Forge, suítes por serviço, `validate_requirements_ids` e `scan_secrets` OK.

## Reversibilidade

Toda a FASE 2 está na branch `chore/project-organization`. Reverter = descartar a branch
ou reverter commits específicos. Baseline: `c724282`.
