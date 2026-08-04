# Validação

## Modelo geral

As regras vêm de `validation_rules` no `layout.yaml`. Cada item é um dict com `ref` (nome da regra) e parâmetros adicionais. O `ValidationEngine` (`validators/engine.py`) despacha para funções em `validators/library.py`.

## Comportamento do motor

- Regras são avaliadas **em ordem**.  
- Algumas falhas tornam o registo **inválido** para seguir ao pipeline (`apply` devolve `False`).  
- Outras apenas **avisam** (`ValidationReport.add_warning`) sem bloquear.

### Refs que podem bloquear (resumo)

| `ref` | Efeito de falha |
|-------|-----------------|
| `required_fields` | Erro por campo ausente; `apply` falha. |
| `date_valid` | Data inválida; `apply` falha. |
| `non_negative` | Não numérico ou negativo; `apply` falha. |
| `annual_numeric_non_negative` | Valor negativo em campo listado; `apply` falha. Valor não numérico gera **warning** e também falha o retorno do handler. |

### Refs principalmente informativas ou mistas

| `ref` | Notas |
|-------|--------|
| `first_day_of_month` | Aviso se o dia não for 1 (usa `_parsed_date` ou campo). |
| `lactating_consistency` | Aviso se `Number_of_Lactating_Cows` e `Lactating_Cows` divergem. |
| `dry_consistency` | Idem para secas. |
| `milk_sales_le_production` | Aviso se vendas superam produção. |
| `weight_range_warning` | Aviso se peso fora de 200–900 kg (intradiário). |

## Regras dinâmicas (anual)

Para `annual_numeric_non_negative` com `__dynamic__: true` no YAML, o pipeline expande `fields` a partir de `numeric_fields.yaml` no diretório do layout.

## Validação estrutural

Falha de leitura do ficheiro (ficheiro inexistente, encoding, CSV corrompido) é capturada **fora** do `ValidationEngine` e regista-se como `STRUCTURAL_PARSE_ERROR`.

## Rejeição parcial e total

- **Parcial:** algumas linhas passam na validação e normalização; outras falham na validação (ou normalização). Status `partial_success`.  
- **Total:** nenhuma linha aceite; status `failure` e flag `all_records_rejected` se as falhas forem por linha.

## Relatório de erros

`ValidationReport` contém:

- `errors` e `warnings` com `ValidationIssue` (código, mensagem, severidade, campo, linha, valor opcional).  
- `rejected_indices` e `rejected_count` derivados de erros com linha.

## Cobertura nos testes

- `test_partial_success_collects_rejected_records` — leite negativo na segunda linha; espera `PARTIAL_SUCCESS` e `_reject_phase == validation`.  
- Testes de layouts V1 com CSV reais (quando `data/` existe) exercitam regras combinadas.  
- Existe um teste por `ref` em `testing/test_validation_refs.py`, mais `test_validation_refs_frozen_set_matches_engine` para sincronizar com `validation_rule_refs()`.

## Extensão

1. Implementar função em `validators/library.py`.  
2. Registar em `_rule_registry()` em `validators/engine.py` com assinatura compatível (`row`, `line_index`, `report`, parâmetros do YAML).  
3. Documentar a nova `ref` no YAML do layout e nesta documentação.  
4. Acrescentar teste em `testing/test_validation_refs.py` e incluir a `ref` em `COVERED_VALIDATION_REFS`.

## API de descoberta

`validation_rule_refs()` em `validators/engine.py` devolve o conjunto de `ref` registadas.

Ver também: [layouts](layouts.md), [extension-guide](extension-guide.md), [testing](testing.md).
