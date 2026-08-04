# Documentação — Camada de Wrappers (EcoFarm OS)

Documentação técnica da camada de **wrappers** para integração de dados heterogêneos de fazendas leiteiras. O objetivo é isolar formatos e semânticas de origem, validar e normalizar registos, produzir metadados de rastreabilidade e preparar projeções para camadas posteriores (armazém analítico, indicadores, ACV, ontologia, ML, dashboards).

## Público-alvo

- Desenvolvedores que mantêm ou estendem o código  
- Engenheiros de dados e integração  
- Operação / produção (pipelines, exportação, auditoria)  
- Contexto acadêmico (arquitetura, contratos, versionamento)

## Premissas documentadas

1. **Núcleo estável** — `LayoutPipeline`, contratos (`contracts.py`) e estratégia de exportação concentram o comportamento principal.  
2. **Layouts extensíveis** — novos layouts são ficheiros sob `layouts/<família>/<versão>/layout.yaml` registados automaticamente.  
3. **Layouts V1 atuais** — `IntradayLayoutV1`, `MonthlyLayoutV1`, `AnnualLayoutV1` (identificadores de catálogo: `intraday:v1`, `monthly:v1`, `annual:v1`).  
4. **API principal enxuta** — entradas públicas: `process_file` e `process_file_auto`.  
5. **Separação de fases** — parsing físico, mapeamento lógico, validação, normalização, harmonização declarativa por layout, mapeamento canónico e exportação pós-wrapper.  
6. **Rastreabilidade** — proveniência, contexto temporal/organizacional, relatórios de validação, manifestos de exportação.  
7. **Exportação `;_;`** — formato delimitado customizado (não CSV RFC de um único carácter).  
8. **Versionamento** — coexistência por `layout_id` e pastas versionadas (`v1`, `v2`, …).  
9. **Ontologia futura** — projeções canónicas atuais são um passo intermédio; unidades e URIs formais ainda não estão no schema.

## Índice da documentação

| Documento | Conteúdo |
|-----------|----------|
| [Visão geral e navegação](README.md) | Este ficheiro |
| [Guia da API](api-guide.md) | Entrada principal, secundárias, metadados |
| [Arquitetura](architecture.md) | Camadas, componentes, decisões, trade-offs |
| [Estrutura do projeto](project-structure.md) | Pastas, módulos, dependências |
| [Componentes centrais](core-components.md) | Classes, protocolos, responsabilidades |
| [Layouts (índice)](layouts.md) | Visão dos layouts V1 e ligações |
| [IntradayLayoutV1](layouts/intraday-v1.md) | Schema, validação, exemplos |
| [MonthlyLayoutV1](layouts/monthly-v1.md) | Schema, validação, ambiguidades |
| [AnnualLayoutV1](layouts/annual-v1.md) | Schema, ano, campos numéricos |
| [Fluxo de processamento](processing-flow.md) | Pipeline passo a passo |
| [Contratos](contracts.md) | Entrada/saída, metadata, pseudo-JSON |
| [Validação](validation.md) | Regras, erros, rejeição parcial/total |
| [Normalização](normalization.md) | Tipos, datas, chaves, famílias |
| [Harmonização](harmonization.md) | Passos declarativos aplicados na normalização |
| [Mapeamento canónico](canonical-mapping.md) | Projeções YAML → vocabulário alvo |
| [Exportação pós-wrapper](export.md) | Pastas, manifest, `;_;`, leitura |
| [Registry e versionamento](registry-and-versioning.md) | Catálogo, V2/V3, fingerprint |
| [Uso em produção](production-usage.md) | Pipelines, lote, auditoria, monitorização |
| [Exemplos](examples.md) | Snippets Python e cenários |
| [Testes](testing.md) | Suíte, cada grupo de testes, interpretação de falhas |
| [Troubleshooting](troubleshooting.md) | Problemas comuns e diagnóstico |
| [Guia de extensão](extension-guide.md) | Novo layout, regras, exportação |
| [FAQ](faq.md) | Perguntas frequentes técnicas |
| [Ontologia: unidades e IRIs](ontology/units-and-iris.md) | Catálogo de unidades, IRIs de exemplo, YAML máquina-legível |

## Como executar testes

A suíte assume que o pacote `wrappers` é importável (por exemplo, diretório pai de `wrappers` no `PYTHONPATH`). Exemplo:

```bash
cd "<diretório que contém a pasta wrappers>"
python -m pytest wrappers/testing -q
```

Alguns testes usam CSV em `wrappers/data/`; se a pasta não existir, esses testes fazem **skip**.

## Documentação legada na raiz do pacote

Existem ficheiros `00_ARQUITETURA_CAMADA_WRAPPERS.md`, `01_ARQUITETURA_WRAPPERS_ESCALAVEL.md` e `02_PERSISTENCIA_E_EXPORTACAO_POST_WRAPPER.md` na raiz de `wrappers/`. A pasta **`docs/`** consolida e atualiza a narrativa; em caso de divergência, prevalece o **código-fonte** e esta pasta `docs/`.

## O que ainda pode ser documentado no futuro

- Contratos OpenAPI/AsyncAPI se a ingestão passar a ser serviço HTTP  
- Manifests Helm / Kustomize concretos do cluster EcoFarm OS (este repositório mantém apenas runbooks de referência)  
- Mais refs de harmonização (conversão de unidades, mapa de sinónimos → IRI) com implementação no código  

---

*Última revisão alinhada ao código do pacote `wrappers` (pipeline simplificado, `catalog_display_name`, exportação `;_;`).*
