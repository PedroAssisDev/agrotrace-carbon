# 10 — Plano de validação pós-reorganização (FASE 2)

Ambiente: isolado via `AGROTRACE_DATA_ROOT` temporário quando aplicável.  
**Não:** reset destrutivo sem confirmação; txs Sepolia; alteração de DBs operacionais.

---

## 1. Pré-checks

- [ ] Commit-base existe; branch `chore/project-organization` (ou nome aprovado)
- [ ] `git status` limpo o suficiente para o escopo
- [ ] `frontend/scripts/scan_secrets.py` (ou equivalente) sem achados críticos
- [ ] Inventário “antes” salvo

## 2. Importação de módulos

Em venv do projeto, importar sem erro:

- [ ] `save_file`
- [ ] `wrappers` / `process_file`
- [ ] `ontology`
- [ ] `orchestration.pipeline` / emissions
- [ ] `model_training_service` (se instalado)
- [ ] provenance / UoW factory
- [ ] blockchain `app` use cases / providers
- [ ] frontend packages usados por `main.py`

## 3. Testes por serviço

| Suíte | Comando típico (confirmar no README do módulo) |
|-------|-----------------------------------------------|
| save-file | unittest / pytest do pacote |
| wrappers | pytest |
| ontology-manager | pytest |
| calculation-service | pytest |
| model-training | pytest |
| traceability | pytest |
| blockchain | pytest (deselect Sepolia live se marcado) |
| Forge | `forge test` em `contracts/` |
| frontend | `pytest frontend/tests` |

## 4. Scripts validate e regressão

- [ ] `python frontend/scripts/run_full_regression.py` (fonte canônica de regressão)
- [ ] Smoke: `run_pipeline_smoke_test.py`
- [ ] Ciclo: `test_full_emission_cycle.py`
- [ ] Confirmar que falhas **pré-existentes** (`validate_emission_calculation_details`, `validate_preliminary_calculation_form`) não são introduzidas pela reorganização; documentar se ainda falham

## 5. Documentação e links

- [ ] Verificador de links relativos Markdown (a criar na FASE 2)
- [ ] Grep paths antigos: `auditoria-capitulo-5`, `auditoria-pos-implementacao`, `docs/decisions/`, `conceptual_model_mrv`, `filter_architecture_mrv`, `IMPLEMENTACAO_ETHEREUM_SEPOLIA`
- [ ] README raiz e `docs/README.md` carregam e apontam arquivos existentes
- [ ] Nenhum doc **atual** afirma 12 telas ou blockchain exclusivamente simulada sem matizar EVM
- [ ] Nenhum caminho pessoal / secret em docs atuais

## 6. Gerador de auditoria

- [ ] `generate_audit_reports.py` com nova fonte de requisitos
- [ ] Validação IDs RF/RNF/CE
- [ ] `docs/auditoria-pos-implementacao/tests` (ou path movido) passam

## 7. Compatibilidade legada

- [ ] Alias `yearly` → `annual` (testes ontology/domain)
- [ ] Redirects legados (smoke manual ou teste)
- [ ] Provider simulado no caminho Dash
- [ ] ABI fallback (teste existente `test_version_manifest` se aplicável)

## 8. Inventário e Git

- [ ] Inventário depois vs antes (`17-before-after-inventory.md`)
- [ ] `git diff` / `git status` resumidos em `18-final-report.md`
- [ ] Lista de moves/removes (`13`, `12`) completa
- [ ] Evidências acadêmicas ainda presentes (paths archive)

## 9. Critério de aprovação da FASE 2

Aprovada se:

1. Regressão não regrediu além das falhas já conhecidas documentadas;
2. Links dos docs atuais válidos;
3. Nenhuma evidência acadêmica perdida;
4. Compat legada testada;
5. Deletion plan respeitado (vazio ou itens registrados);
6. Git permite reverter.

---

## Entregáveis de validação

Preencher na FASE 2:

- `15-links-validation.md`
- `16-tests-and-regression.md`
- `17-before-after-inventory.md`
- `18-final-report.md`
