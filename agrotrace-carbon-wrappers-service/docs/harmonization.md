# Harmonização

## Papel na arquitetura

A harmonização situa-se **depois** da normalização e **antes** da projeção canónica. Separa:

- **Normalização** — tipos, datas, contextos temporais e organizacionais básicos.  
- **Harmonização** — alinhamento semântico adicional (sinónimos, políticas de desambiguação, preenchimento derivado) configurável sem misturar com conversão de tipos.

## Configuração no YAML

Bloco opcional no `layout.yaml`:

```yaml
harmonization:
  steps:
    - ref: nome_da_ref
```

Os passos executam-se em ordem; cada um recebe o dict produzido pelo passo anterior.

## Implementação actual

A harmonização declarativa é aplicada em `normalizers/library.py` por
`normalizers.harmonization.apply_layout_harmonization(layout_doc, record)`:

- Sem chave `harmonization`, ou `steps` vazio: devolve o mesmo dict (identidade).  
- `ref` desconhecida: é ignorada para preservar robustez do pipeline.

### Ref implementada: `strip_whitespace_strings`

Remove espaços à esquerda e direita em strings.

- Com lista `fields: [chave1, chave2]`: só essas chaves são trimadas (se valor for `str`).  
- Sem `fields` ou lista vazia: todas as chaves com valor `str` são trimadas, exceto nomes que começam por `_`.

Código: `normalizers/harmonization.py` (`strip_whitespace_strings` + `apply_layout_harmonization`).

**Exemplo em produção:** `MonthlyLayoutV1` inclui trim de `property_id` após a normalização.

### Novas refs

1. Implementar o comportamento em `normalizers/library.py`.  
2. Adicionar tratamento da nova `ref` em `apply_layout_harmonization`.  
3. Documentar aqui e testar em `testing/test_harmonization_steps.py`.

## Testes

- `testing/test_harmonization_steps.py` — trim e aplicação do YAML `monthly:v1`.

## Relação com o modelo canónico

A harmonização opera no **espaço do layout lógico**. A projeção canónica (`CanonicalMappingEngine`) mapeia para nomes alvo estáveis (ex.: `Property.identifier`). Futuras ontologias podem exigir harmonização mais rica antes dessa projeção.

Ver também: [processing-flow](processing-flow.md), [canonical-mapping](canonical-mapping.md), [extension-guide](extension-guide.md), [ontology/units-and-iris](ontology/units-and-iris.md).
