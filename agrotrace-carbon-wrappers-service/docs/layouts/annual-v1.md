# AnnualLayoutV1

## Objetivo

Ingerir inventário e indicadores **anuais** da propriedade: rebanho, pesos médios, leite, alimentação, energia, fertilizantes e outras variáveis relevantes para produtividade e pegada ambiental.

## Identificador e versão

- **`layout_id`:** `annual:v1`  
- **`catalog_display_name`:** `AnnualLayoutV1`  
- **`version`:** `1.0`  
- **Ficheiros:** `layouts/annual/v1/layout.yaml`, `layouts/annual/v1/numeric_fields.yaml`

## Formato físico

- CSV com `;`, UTF-8, cabeçalho na primeira linha.

## Modo de schema

- **`schema.mode: snake_case_headers`** — os cabeçalhos físicos são normalizados para `snake_case` e tornam-se chaves do registo.  
- **`schema.required`:** inclui pelo menos `property_name`.  
- **`numeric_fields_file`:** lista de campos tratados como numéricos e sujeitos a validação não negativa.

## Campos (cabeçalhos físicos esperados)

A lista completa segue o enunciado do projeto (de `Property_Name` a `Organic_Fertilizer`). O ficheiro `numeric_fields.yaml` enumera os campos numéricos conhecidos para validação e parsing; colunas extra no CSV permanecem como texto normalizado se não estiverem nessa lista.

## Granularidade

- **Temporal:** intervalo anual (ano de referência injectado no registo como `year`).  
- **Organizacional:** propriedade (`property_name` como identificador no contexto por registo).

## Ano de referência

Ordem de precedência prática:

1. `year` passado em `process_file(..., year=…)` ou em opções.  
2. `ProcessingContext(year=…)`.  
3. Ano extraído do **nome** do ficheiro (`infer_year_from_source_uri`), se entre 2000 e 2100.  
4. Se nada for encontrado: **warning** e uso do ano UTC corrente.

## Validações

- `required_fields` para `property_name`.  
- `annual_numeric_non_negative` sobre o conjunto dinâmico de campos numéricos (valores negativos = erro; não numérico com valor presente = warning e falha do handler).

## Normalização

- Campos numéricos em `float`; strings trimadas; `year` no dict.

## Ambiguidades semânticas

- Muitos campos de alimentação e energia sem **unidade explícita** no schema (toneladas, kg, kWh, litros, etc.). Risco elevado para ACV até haver ontologia ou conversões.  
- Nomes como `Total`, `Other_Feed`, `DMI_Check` exigem definição de negócio para mapeamento canónico fiável.

## Mapeamento canónico preliminar

O YAML actual projeta apenas um subconjunto (ex.: `Property.name`, `AnnualFarmInventory.referenceYear`, `totalMilkProduction`). A maioria das colunas **ainda não** tem alvo canónico declarado.

## Exemplo de entrada (mínimo)

```csv
Property_Name;Lactating_Cows
Farm;10
```

Com `year=2022` nas opções ou contexto.

## Erros comuns

- Esquecer o ano quando o nome do ficheiro não contém quatro dígitos úteis.  
- Valores negativos em campos numéricos.  
- Menos colunas que o mínimo esperado na **deteção** automática (o layout anual usa `min_column_count` para desambiguar).

## Deteção

Prioridade mais baixa que intradiário e mensal; exige número mínimo de colunas no cabeçalho.

Ver também: [registry-and-versioning](../registry-and-versioning.md), [normalization](../normalization.md), [canonical-mapping](../canonical-mapping.md).
