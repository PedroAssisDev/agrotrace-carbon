# Guia de extensão

## Adicionar um novo layout

1. Criar pasta `layouts/<familia>/v1/` (ou `v2` se for segunda versão da mesma família).  
2. Copiar um `layout.yaml` existente como modelo.  
3. Definir `layout_id` **único** (ex.: `custom:v1`).  
4. Preencher `catalog_display_name`, `physical`, `schema`, `granularity`, `validation_rules`, `canonical_mapping`, `detection`.  
5. Executar testes com um CSV mínimo em `pytest` ou script.  
6. Documentar em `docs/layouts/` se for layout estável.

## Nova versão de layout (V2)

1. Manter V1 intacto.  
2. Adicionar `layouts/<familia>/v2/layout.yaml` com `layout_id` `familia:v2`.  
3. Ajustar deteção para não colidir (cabeçalhos distintos, `priority`, `min_score`, `min_column_count`).  
4. Migrar consumidores para `v2` de forma explícita.  
5. Planejar deprecação de V1.

## Novas regras de validação

1. Implementar função em `validators/library.py` (assinatura compatível com uso no motor).  
2. Registar em `_rule_registry()` em `validators/engine.py` com chave `ref`.  
3. Adicionar entrada em `validation_rules` no YAML.  
4. Escrever teste unitário com linha que passa e linha que falha.

## Novas regras de normalização

- **Nova família:** implementar finalizador e registar com `NormalizationEngine.register_family_finalizer` ou adicionar ao mapa `_FAMILY_FINALIZERS` em `normalizers/engine.py`.  
- **Família existente:** alterar `finalize_*_row` em `normalizers/library.py` com cuidado para não quebrar V1.

## Harmonização declarativa

1. Implementar função em `normalizers/library.py`.  
2. Registar a nova `ref` em `normalizers/harmonization.py` (`apply_layout_harmonization`).  
3. Documentar a `ref` em `docs/harmonization.md`.  
4. Testar em `testing/test_harmonization_steps.py`.  
5. Layouts sem bloco `harmonization` mantêm identidade.

## Novo mapeamento canónico

Editar `canonical_mapping.projections` no YAML: pares `logical` / `target`. Garantir que `logical` existe após normalização.

## Nova estratégia de exportação

Opções:

- Parametrizar `ExportConfiguration` (extensão de campos).  
- Subclassificar `OutputWriter` ou introduzir interface de “sink” se o projeto crescer (refactor maior).  
- Para outro formato (Parquet), recomenda-se camada à parte que leia `ProcessingResult` sem alterar o núcleo.

## Checklist de manutenção

- Atualizar `docs/` e testes.  
- Verificar `source_schema_version` após mudar YAML.  
- Evitar `layout_id` duplicado.

Ver também: [registry-and-versioning](registry-and-versioning.md), [testing](testing.md).
