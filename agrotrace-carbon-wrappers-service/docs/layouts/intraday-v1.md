# IntradayLayoutV1

## Objetivo

Ingerir observações intradiárias de leite e peso por animal (tag), para monitorização e modelos ao nível animal e dia.

## Identificadores

- layout_id: `intraday:v1`
- catalog_display_name: `IntradayLayoutV1`
- YAML: `layouts/intraday/v1/layout.yaml`

## Formato físico

CSV, delimitador vírgula, UTF-8, com cabeçalho.

## Campos

- Date → date (obrigatório, tipo data)
- Tag → animal_id (obrigatório, texto)
- Milk → milk (obrigatório, número)
- Weight → weight (obrigatório, número)

## Granularidade

Temporal: instante (dia). Organizacional: animal.

## Validações

Obrigatórios; data válida; milk e weight não negativos; aviso de peso fora de 200–900 kg.

## Normalização

ISO para data; floats para leite e peso; contextos `_temporal_context` e `_organizational_context` por registo.

## Ambiguidade

Tag assume identificador de animal; outras fontes semânticas exigem revisão na ontologia.

## Mapeamento canónico

Exemplos no YAML: observação de leite, identificador animal, valor de peso.

## Exemplo CSV

```
Date,Tag,Milk,Weight
2021-01-01,A1,10.5,500
```

## Erros comuns

Datas inválidas; valores negativos; cabeçalhos incorretos; delimitador errado.

Ver também: ../validation.md, ../normalization.md, ../export.md
