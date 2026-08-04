# Catálogo de unidades e ligação a IRIs / ontologia

Este documento define uma **camada semântica de referência** para o EcoFarm OS. O código dos wrappers **não aplica** automaticamente conversões com base neste catálogo; o ficheiro serve para alinhamento entre equipas, evolução para RDF/OWL e enriquecimento futuro do pipeline (pós-harmonização ou camada de integração).

## Ficheiro máquina-legível

Ver [field-units-catalog.yaml](field-units-catalog.yaml) — lista de campos lógicos ou padrões, unidade sugerida, notas e IRI de exemplo (vocabulários externos ou namespace EcoFarm).

## Convenções de IRI

- **QUDT** — Quantities, Units, Dimensions and Types (`http://qudt.org/schema/qudt/`, `http://qudt.org/vocab/unit/…`).  
- **Schema.org** — propriedades de alto nível quando aplicável (`https://schema.org/`).  
- **EcoFarm** — namespace reservado para conceitos internos até publicação formal: `https://ontology.ecofarm.example/` (substituir pelo domínio real).

## Uso recomendado no fluxo actual

1. **Ingestão (wrappers)** — mantém valores como na fonte; opcionalmente documentar unidade esperada no YAML do layout (`unit_hint` futuro).  
2. **Harmonização / integração** — ler `field-units-catalog.yaml` ou grafo ontológico e anotar registos com `quantity kind` + `unit` + `value_SI` se houver conversão.  
3. **ACV / indicadores** — consumir apenas registos já normalizados em SI ou com metadado explícito.

## Relação com layouts V1

| Domínio | Campos típicos | Unidade sugerida (negócio) |
|---------|----------------|----------------------------|
| Intradiário | milk | L ou kg (definir na propriedade) |
| Intradiário | weight | kg |
| Mensal | milk_production, milk_sales | L, L |
| Mensal | area_used_for_dairy_activity | ha |
| Anual | totais de alimentação | kg MS ou t (explicitar no catálogo) |
| Anual | eletricidade | kWh |

O YAML `field-units-catalog.yaml` detalha entradas e IRIs de exemplo.

## Próximos passos técnicos (fora do âmbito mínimo dos wrappers)

- Gerar triplos RDF a partir de `ProcessingResult` + catálogo.  
- Validar unidades com SHACL sobre o grafo canónico.  
- Ligar `canonical_mapping.target` a object properties OWL.

Ver também: [../canonical-mapping.md](../canonical-mapping.md), [../harmonization.md](../harmonization.md).
