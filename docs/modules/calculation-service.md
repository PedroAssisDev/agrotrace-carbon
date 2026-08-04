# Módulo: calculation-service

## Finalidade

Calcular emissões (CO₂e) por fazenda/período a partir dos dados normalizados, produzindo
resultados **preliminares** com registro dos parâmetros usados.

## Responsabilidades

- Calcular emissões com fórmulas IPCC/ECOFARM e GWP.
- Registrar os parâmetros e a explicação do cálculo (`calc_explanation_v1`).

## Não faz

- Não publica nem ancora. Não é fonte de predição (isso é do model-training-service).

## Contratos com o frontend

- `from orchestration.pipeline import compute_farm_period_emissions`.
- `FarmPeriodInput`, `gwp_ipcc_ar4`; adapter `frontend/services/calculation_adapter`.

## Entradas / saídas

- Entrada: dados de fazenda/período (granularidade `monthly` | `annual` como base de cálculo).
- Saída: resultado preliminar + `factors_used` / explicação.

## Compatibilidade legada

`TemporalScope.YEARLY` é aceito apenas como alias de leitura de `annual` — não remover
sem migração; ver [../domain/calculations.md](../domain/calculations.md).

## Limitações conhecidas

- Validadores `validate_emission_calculation_details` e `validate_preliminary_calculation_form`
  falhavam na última auditoria (série por gás no detalhe) — RF008/RF009/RNF005 parciais.

## Testes e comandos

- `pytest` no serviço; `validate_calculation_review`, `validate_preliminary_calculation_view`.

## Relacionados

- RF008, RF009 (parciais), RF013–RF015; RNF005.
- Detalhe: `agrotrace-carbon-calculation-service/README.md`, `REVISAO_TECNICA_CALCULOS.md`.
