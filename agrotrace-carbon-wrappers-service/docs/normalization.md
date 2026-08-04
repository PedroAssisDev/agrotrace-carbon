# Normalização

## Objetivo

Converter valores brutos em tipos consistentes, preencher campos derivados (por exemplo fim de período mensal), e injetar contexto temporal e organizacional por registo em `_temporal_context` e `_organizational_context`, antes da harmonização e da projeção canónica.

## Onde ocorre

`NormalizationEngine.finalize_record` em `normalizers/engine.py`, com lógica em `normalizers/library.py` e dispatch por `layout_family`.

## Tipos por família

- **Intradiário:** `milk` e `weight` como float; data ISO; `animal_id` com trim.  
- **Mensal:** campos em `MONTHLY_NUMERIC_KEYS` como float; `period_start` e `period_end` em ISO.  
- **Anual:** campos listados em `numeric_fields.yaml` como float; resto string trimada; campo `year` adicionado.

## Nomes e aliases

Aliases no YAML mapeiam cabeçalhos físicos para chaves lógicas. No anual, cabeçalhos passam por `to_snake_case`.

## Unidades

Não há conversão de unidades no código actual. Valores numéricos são interpretados sem metadado de unidade no schema. Para ACV e relatórios físicos, prevê-se extensão com ontologia ou schema enriquecido.

## Datas

`parse_date` aceita formatos comuns nos primeiros 10 caracteres. O anual obtém ano de opções, contexto, nome do ficheiro ou ano atual com aviso.

## Campos ausentes

Valores vazios ou marcadores podem normalizar-se a `None` no fluxo anual. No mensal, vazios viram `None` no registo final.

## Contexto por registo

Intradiário: instante e granularidade animal. Mensal: intervalo mensal e propriedade. Anual: intervalo anual e propriedade por nome.

## Risco de deriva

`MONTHLY_NUMERIC_KEYS` deve acompanhar o schema YAML dos campos numéricos mensais.

## Extensão

Nova família: usar `register_family_finalizer` ou entrada em `_FAMILY_FINALIZERS`. Novos numéricos mensais: atualizar YAML e a lista em código até haver geração automática.

Ver também: [harmonization](harmonization.md), [layouts](layouts.md).
