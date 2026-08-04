# Resumo executivo — auditoria pós-implementação

**Data (UTC):** 2026-08-04T13:34:02.916823+00:00  
**Dissertação:** `frontend/main (7).pdf`  
**Git:** branch `master`, **0 commits** (sem SHA)  
**Isolamento:** `AGROTRACE_DATA_ROOT` temporário via `run_full_regression.py`  
**Bancos operacionais:** `blockchain_service.db` inalterado; `provenance.db` mudou de hash após checkpoint WAL (ver `10-verificacao-git-e-dados.md`)  

## Conclusão geral

A implementação cobre a maior parte dos RF001–RF021, RNF001–RNF012 e das **nove** decisões oficiais do Cap. 4.2.3 (mais o complemento 4.5.10), com evidência executada em ambiente isolado (37/39 passos da regressão). Permanecem lacunas materiais: **Lot ausente na OWL**, **dois validadores de cálculo/detalhe falhando**, **Capítulo 5 ainda não redigido no PDF**, **ausência de commit Git** e **capturas visuais pendentes**.

## Classificação de prontidão (Capítulo 5)

**PRONTA COM LIMITAÇÕES DECLARADAS**

## Contagens (automáticas)

| Grupo | ATENDIDO | PARCIAL | NÃO ATENDIDO | NÃO VERIFICÁVEL | NÃO APLICÁVEL |
|-------|----------|---------|---------------|-----------------|---------------|
| RF (21) | 18 | 3 | 0 | 0 | 0 |
| RNF (12) | 10 | 2 | 0 | 0 | 0 |
| Decisões Cap. 4.2.3 (9) | 9 | 0 | 0 | 0 | 0 |
| CE (5) | 3 | 2 | 0 | 0 | 0 |

## Itens atendidos (destaques)

- Recuperação do bruto (RF002), correção/recálculo (RF010), predição separada (RF011), publicação/gate blockchain (RF016–RF021 em provider simulado + Forge).
- Canonicalização única `json_canonical_v1` fail-closed; VersionManifest; append-only com triggers; scan_secrets.
- Regressão: save-file, wrappers, ontology, calculation, model-training, traceability, blockchain, forge, frontend_tests, smoke, full emission cycle.

## Itens parciais

- **RF005 / RNF006 / CE1:** enums lot/daily/monthly/annual presentes; **classe Lot inexistente na OWL**.
- **RF008 / RF009 / RNF005 / CE2:** `validate_emission_calculation_details` (série por gás) e `validate_preliminary_calculation_form` (factor_catalog ausente) **FAIL**.

## Não atendidos

- Nenhum RF/RNF classificado como NÃO ATENDIDO nesta auditoria.

## Riscos críticos

1. Validadores de detalhe/form de cálculo falham — risco para evidências Cap. 5 sobre explicabilidade/UI de cálculo.
2. Lot organizacional incompleto semanticamente (OWL).
3. Repositório sem commits — sem baseline SHA para auditorias futuras.
4. Sepolia não reexecutada (evidência documental preexistente apenas).
5. Hash de `provenance.db` operacional mudou (provável checkpoint WAL) — ver `10-verificacao-git-e-dados.md`.

## Recomendação Cap. 5

Pode redigir o Capítulo 5 **declarando limitações**: Lot OWL, falhas dos dois validate_*, ausência de reancoragem Sepolia nesta rodada, e plano de figuras UI. Corrigir os dois validadores e o Lot OWL antes de afirmar atendimento pleno de RF005/RF008/RF009.
