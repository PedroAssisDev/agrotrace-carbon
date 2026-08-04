# Registo de layouts e versionamento

## O que é um layout

Um **layout** é a especificação completa de como interpretar um tipo de ficheiro: formato físico, schema lógico, validação, mapeamento canónico, granularidade e metadados de deteção. No código, é um documento YAML carregado pelo `LayoutRegistry`.

## Layout versus versão

- **`layout_id`** — identificador único de catálogo, convencionalmente `familia:vx` (ex.: `monthly:v1`).  
- **Pasta `v1`, `v2`** — convenção de disco sob `layouts/<familia>/`.  
- **Campo `version` no YAML** — versão semântica do documento (ex.: `"1.0"`); pode diferir do sufixo do `layout_id`.  
- **`catalog_display_name`** — rótulo humano (ex.: `MonthlyLayoutV1`) para documentação e manifest.

## Como o registry funciona

`LayoutRegistry` (`registry/file_registry.py`):

1. Percorre `layouts/` com `rglob("layout.yaml")`.  
2. Carrega cada ficheiro com PyYAML.  
3. Indexa por `layout_id`.  
4. Se o mesmo `layout_id` aparecer duas vezes, a última descoberta **substitui** a anterior e regista-se um **aviso** no logger.

## Adicionar um novo layout

1. Criar `layouts/<nova_familia>/v1/layout.yaml` com `layout_id` único.  
2. Definir `physical`, `schema`, `validation_rules`, `canonical_mapping`, `granularity`, `detection` conforme necessário.  
3. Opcional: recursos auxiliares na mesma pasta (`numeric_fields.yaml`, etc.).  
4. Reiniciar processos ou recriar `LayoutRegistry` para releitura (não há hot-reload automático).

## Coexistência entre versões

Layouts `intraday:v1` e `intraday:v2` podem coexistir: IDs distintos e pastas distintas. O pipeline escolhe o ID passado explicitamente ou o melhor score na deteção (ajustar `detection.priority` e limiares).

## Compatibilidade retroativa

- Manter `layout_id` antigo estável para consumidores.  
- Introduzir `v2` sem remover `v1` até migração completa.  
- `source_schema_version` (hash do YAML) muda com qualquer edição no documento: útil para auditoria, mas sensível a mudanças triviais.

## Planejar V2 e V3

1. Copiar `v1/layout.yaml` para `v2/layout.yaml` com novo `layout_id`.  
2. Ajustar schema e regras; migrar consumidores para o novo ID.  
3. Atualizar deteção para não colidir com V1 (cabeçalhos exclusivos ou `min_column_count` / `min_score`).  
4. Documentar diferenças semânticas e plano de descontinuação de V1.

## Fingerprint (`source_schema_version`)

`source_schema_fingerprint` calcula SHA-256 do JSON serializado do **documento completo** do layout (chaves ordenadas). Qualquer alteração no YAML altera o hash truncado exportado como `sha256:…`.

**Limitação:** comentários em YAML não entram no dict Python; alterações só em comentários **não** mudam o hash. Alterações de formatação irrelevantes ainda podem mudar o dict dependendo do parser.

Ver também: [extension-guide](extension-guide.md), [architecture](architecture.md).
