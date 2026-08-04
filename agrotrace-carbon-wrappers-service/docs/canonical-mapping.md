# Mapeamento canónico preliminar

## Objetivo

Fornecer uma **projeção declarativa** dos campos lógicos do layout para identificadores de domínio estáveis (ex.: `MilkProductionObservation.observedAt`), como passo intermédio antes de um grafo ontológico completo.

## Onde se define

Bloco `canonical_mapping` no `layout.yaml`:

```yaml
canonical_mapping:
  version: "1.0"
  projections:
    - logical: date
      target: MilkProductionObservation.observedAt
```

## Motor

`CanonicalMappingEngine` (`mappers/engine.py`):

- `project_record` — para cada projeção, se `logical` existir no registo e não começar por `_`, copia para `target`.  
- `project_batch` — aplica a todos os registos; devolve dict com chave `projections` (lista) e metadados `layout_family`, `layout_id`.

## Momento no pipeline

Após processar todas as linhas, o pipeline constrói uma lista de registos **sem chaves cujo nome começa por `_`** e chama `project_batch`. Os campos internos `_temporal_context` e `_organizational_context` **não** entram na projeção por essa convenção de strip.

## Limitações (honestas)

- Não valida cardinalidades nem unidades.  
- Não resolve identidade de entidades (ex.: mesma propriedade com códigos diferentes).  
- O conjunto de projeções no YAML dos layouts V1 é **parcial** (sobretudo anual); muitas colunas físicas existem no ficheiro mas não têm alvo canónico declarado ainda.

## Evolução para ontologia

Recomenda-se:

- Substituir ou complementar `target` string por IRIs ou QNames resolvidos.  
- Acrescentar metadados de unidade e tipo semântico no YAML ou num registo separado.  
- Gerar automaticamente documentação a partir do catálogo.

Ver também: [layouts](layouts.md), [contracts](contracts.md).
