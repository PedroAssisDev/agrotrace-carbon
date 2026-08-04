# Layouts V1 — visão geral

Os três layouts suportados em catálogo são identificados por:

| Rótulo humano (`catalog_display_name`) | `layout_id` | Família | Pasta |
|----------------------------------------|-------------|---------|--------|
| IntradayLayoutV1 | `intraday:v1` | intraday | `layouts/intraday/v1/` |
| MonthlyLayoutV1 | `monthly:v1` | monthly | `layouts/monthly/v1/` |
| AnnualLayoutV1 | `annual:v1` | annual | `layouts/annual/v1/` |

## Delimitadores de entrada (ficheiro fonte)

- **Intradiário:** vírgula `,`  
- **Mensal e anual:** ponto e vírgula `;`

Isto **não** confunde com o separador de **exportação** pós-wrapper (`;_;`), que é independente.

## Documentação detalhada

- [IntradayLayoutV1](layouts/intraday-v1.md)  
- [MonthlyLayoutV1](layouts/monthly-v1.md)  
- [AnnualLayoutV1](layouts/annual-v1.md)

## Campos esperados (resumo do negócio)

Os cabeçalhos físicos esperados alinham-se com as listas do enunciado do projeto; o YAML pode declarar aliases adicionais ou campos extra (por exemplo indicadores opcionais no mensal).

## Deteção automática

`detect_layout_id` usa a primeira linha não vazia e compara com cada layout registado. Prioridades configuráveis no YAML (`detection.priority`). O anual exige número mínimo de colunas para não colidir com outros CSV `;`.

Ver também: [registry-and-versioning](registry-and-versioning.md), [validation](validation.md).
