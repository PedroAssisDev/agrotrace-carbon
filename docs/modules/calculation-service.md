# Módulo: calculation-service

## Visão geral

Calcular emissões (CO₂e) por fazenda/período a partir dos dados normalizados, produzindo
resultados **preliminares** com registro dos parâmetros usados.

**Posição:** etapa operacional 6 (`calculation`) do orquestrador. Não publica, não ancora
e não é fonte de predição (isso é do model-training + `forecast_inference`).

## Responsabilidades

- Calcular emissões com fórmulas IPCC/ECOFARM e GWP.
- Registrar os parâmetros e a explicação do cálculo (`calc_explanation_v1`).

## Contratos com o frontend

- `from orchestration.pipeline import compute_farm_period_emissions`
- `FarmPeriodInput`, `gwp_ipcc_ar4`
- Adapter: `frontend/services/calculation_adapter.py`

Implementado em: `agrotrace-carbon-calculation-service/orchestration/pipeline.py`.

## Entradas / saídas

- **Entrada:** dados de fazenda/período (granularidade `monthly` | `annual` como base de
  cálculo). Cobertura típica: fermentação entérica, manejo de dejetos, fertilizantes,
  energia, totais CO₂e e intensidade.
- **Saída:** resultado preliminar + `factors_used` / explicação.
- **Persistência:** nenhuma no serviço (puro); o frontend grava no ciclo JSON e na
  proveniência.

O frontend monta parâmetros (entradas, fatores, GWP explícito via
`emissions.defaults.gwp_ipcc_ar4`) e registra o resultado preliminar com hash. Não aplica
GWP silencioso por default local do FE. Resultados permanecem preliminares até aprovação
e publicação do manifesto.

## Compatibilidade legada

`TemporalScope.ANNUAL` é aceito apenas como alias de leitura de `annual` — não remover
sem migração. Ver [../domain/temporal-and-organizational-granularity.md](../domain/temporal-and-organizational-granularity.md).

## Limitações conhecidas

- Validadores `validate_emission_calculation_details` e
  `validate_preliminary_calculation_form` podem falhar em detalhes de série por gás —
  RF008/RF009/RNF005 parciais conforme auditoria.

## Testes e comandos

```bash
cd agrotrace-carbon-calculation-service
pytest
```

No frontend: `validate_calculation_review`, `validate_preliminary_calculation_form`,
`validate_emission_calculation_details`.

## Relacionados

- RF008, RF009 (parciais), RF013–RF015; RNF005.
- README do serviço: `agrotrace-carbon-calculation-service/README.md`.
- Revisão técnica histórica: `REVISAO_TECNICA_CALCULOS.md` (não é índice operacional).
