# MonthlyLayoutV1

## Objetivo

Dados mensais ao nível da propriedade: leite, vendas, preço, pessoal, área e estrutura do rebanho.

## Identificadores

- layout_id: `monthly:v1`
- catalog_display_name: `MonthlyLayoutV1`
- YAML: `layouts/monthly/v1/layout.yaml`

## Formato físico

CSV com delimitador ponto e vírgula, UTF-8, cabeçalho na primeira linha.

## Campos principais (físico → lógico)

Property → property_id. Period → period_start. Milk_Production → milk_production. Milk_Sales → milk_sales. Milk_Gross_Price → milk_gross_price. Number_of_Lactating_Cows → number_of_lactating_cows. Employees_During_the_Month → employees_during_the_month. Area_Used_for_Dairy_Activity → area_used_for_dairy_activity. Reproducers → reproducers. Lactating_Cows → lactating_cows. Dry_Cows → dry_cows. Pregnant_Heifers → pregnant_heifers. Heifers_in_Raising → heifers_in_raising. Suckling_Calves_female e male → campos lógicos homólogos. Male_Calves_in_Raising, Male_Calves_in_Fattening. Draft_and_Breeding_Bulls. Equines_and_Mules. Number_of_Dry_Cows → number_of_dry_cows.

O YAML pode incluir campos opcionais extra (aliases adicionais).

## Granularidade

Temporal: intervalo mensal com period_end derivado. Organizacional: propriedade.

## Validações

Obrigatoriedade conforme schema; data válida; aviso se o período não for primeiro dia do mês; não negativos onde definido; avisos de consistência entre pares lactação/secas e vendas versus produção.

## Ambiguidades

Dry_Cows versus Number_of_Dry_Cows e Lactating_Cows versus Number_of_Lactating_Cows: o código emite aviso se ambos existirem e diferirem. Unidades não declaradas no YAML.

## Normalização

Lista MONTHLY_NUMERIC_KEYS em código deve acompanhar campos numéricos do schema.

## Exemplo CSV

```
Property;Period;Milk_Production;Milk_Sales
P1;2021-01-01;100;90
```

## Harmonização

O `layout.yaml` inclui o passo `strip_whitespace_strings` em `property_id` (ver ../harmonization.md).

## Erros comuns

Delimitador errado; período inválido; inconsistências entre contagens; produção ou vendas negativas.

Ver também: ../validation.md, ../normalization.md, ../harmonization.md
