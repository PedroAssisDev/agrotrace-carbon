# Arquitetura geral — Camada de Wrappers

## Objetivo e problema

Fazendas leiteiras recebem dados em ficheiros e layouts distintos (intradiário, mensal, anual), com delimitadores, cabeçalhos e convenções diferentes. Consumir isso diretamente nas camadas de integração, indicadores ou ACV acopla o resto do sistema à heterogeneidade.

A camada de wrappers isola essa heterogeneidade num catálogo declarativo (`layout.yaml`), valida e normaliza registos, produz contratos estáveis com proveniência e contexto temporal ou organizacional, exporta opcionalmente artefactos delimitados por `;_;` com manifest, e projeta um vocabulário canónico preliminar para evolução futura para ontologia.

## Relação com a arquitetura maior

As fontes heterogêneas (CSV e futuros formatos) entram nos wrappers; a saída alimenta integração, armazém analítico, indicadores produtivos e ambientais, ACV, ontologia, ML e dashboards. O wrapper não substitui o modelo canónico final nem o armazém: prepara dados e metadados.

## Camadas lógicas

- **Catálogo:** `LayoutRegistry`, ficheiros em `layouts/**/layout.yaml`
- **Parsing físico:** `read_csv_rows` conforme bloco `physical`
- **Mapeamento lógico:** aliases para nomes lógicos ou modo `snake_case_headers`
- **Validação:** `ValidationEngine` com regras por `ref`
- **Normalização:** `NormalizationEngine` por `layout_family`
- **Harmonização declarativa:** passos YAML aplicados em `normalizers.library.apply_layout_harmonization`
- **Mapeamento canónico:** `CanonicalMappingEngine` com projeções do YAML
- **Exportação:** `ExportConfiguration`, `OutputWriter`
- **Entradas públicas:** `process_file`, `process_file_auto`

## Fluxo macro

1. Resolver `layout_id` (explícito ou `process_file_auto` com deteção).
2. Carregar YAML e diretório do layout.
3. Ler linhas CSV.
4. Por linha: mapear, validar, normalizar, harmonizar (se configurado), acumular.
5. Projeção canónica em lote (sem chaves internas que começam por `_` para o batch canónico).
6. Construir `ProcessingResult` com metadata, proveniência, relatório e `rejected_records`.
7. Opcionalmente `persist_processing_result` se `export_config` for passado a `process_file`.

A projeção canónica é calculada após o processamento linha a linha. A exportação é opcional no fim de `process_file`.

## Decisões arquiteturais

- Layouts como dados em YAML reduzem alterações de código para novos cabeçalhos.
- Regras de validação referenciadas por `ref` concentram implementação em Python; novas `ref` exigem código.
- Separador de saída `;_;` evita ambiguidades com vírgula e ponto e vírgula nas entradas; a serialização não usa o módulo `csv` da stdlib com delimitador de um só carácter.
- `source_schema_version` usa hash do documento YAML para governança; alterações no YAML mudam o hash.
- Superfície única de saída: `ProcessingResult`.

## Trade-offs

YAML flexível versus risco de deriva face às funções de validação ou normalização. Deteção automática de layout melhora UX mas pode ser ambígua sem prioridades e limiares no YAML. Harmonização declarativa simples mantém o núcleo enxuto ao custo de menos extensibilidade plugável.

## Inconsistências conhecidas

- `MONTHLY_NUMERIC_KEYS` em código duplica o schema mensal no YAML.
- Pandas em `requirements.txt` pode não ser usado diretamente pelo núcleo; confirmar no vosso ambiente.
- `_inject_parsed_dates` só trata o primeiro campo `type: date` do schema.

Ver também: [project-structure](project-structure.md), [processing-flow](processing-flow.md), [core-components](core-components.md).
