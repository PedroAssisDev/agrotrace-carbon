# AgroMRV-O Lite — Documentação Técnica

## 1. O que é a AgroMRV-O Lite

A AgroMRV-O Lite é uma ontologia de domínio autocontida para integração semântica de dados agropecuários em sistemas digitais de MRV. Ela foi projetada para representar dados organizacionais, temporais, produtivos, nutricionais, energéticos, ambientais e de cálculo de emissões em propriedades leiteiras. Em vez de criar uma classe para cada coluna dos datasets, a ontologia adota um modelo orientado a observações, no qual cada campo é mapeado para uma variável canônica observada em um contexto organizacional e temporal. Essa estratégia reduz complexidade, facilita manutenção e permite incorporar novos layouts sem redesenhar a hierarquia de classes.

A ontologia também inclui um módulo de cálculo, responsável por representar semanticamente os métodos de cálculo, suas funções Python correspondentes, suas entradas, gases, fontes de emissão, parâmetros e resultados. A execução matemática permanece na API Python, enquanto a ontologia documenta e integra semanticamente os métodos, execuções e resultados. Essa separação melhora testabilidade, transparência e manutenção.

## 2. Por que não usa PROV nem ontologias externas de domínio

Na primeira versão, a AgroMRV-O Lite:

- **Não utiliza PROV-O** — proveniência detalhada ficará para módulos futuros (traceability/blockchain).
- **Não importa ontologias externas de domínio** (OWL-Time, SOSA/SSN, QUDT, DQV, ORG, GeoSPARQL, DCAT, SKOS).
- Usa apenas vocabulários técnicos básicos: **RDF, RDFS, OWL e XSD**.
- Permanece **autocontida e compatível com OWL 2**, facilitando deploy e manutenção sem dependências semânticas externas.

## 3. Papel no fluxo do projeto

```text
Wrappers / Normalização  →  CSV/DataFrame (;_;)  →  AgroMRV-O Lite  →  Export OWL/RDF/TTL
                                                              ↓
                                                    Cálculos Python (emissions/)
```

A ontologia **não executa cálculos**. Ela representa semanticamente:

- quais dados existem (observações);
- em qual contexto organizacional e temporal;
- quais métodos de cálculo existem e quais funções Python os implementam;
- quais parâmetros (incluindo GWP) são exigidos.

## 4. Relação com wrappers, dados normalizados e cálculos

| Camada | Responsabilidade |
|--------|------------------|
| **Wrappers service** | Parse de layouts, normalização, export CSV com `_;_` e contextos JSON |
| **AgroMRV-O Lite** | Modelo semântico, catálogos, população ABox, exportação |
| **Calculation service** | Funções puras em `emissions/`, orquestração em `batch_runner.py` |

O módulo de ontologia referencia paths de cálculo como metadados (`hasModulePath`, `hasFunctionName`), sem importar o calculation-service em runtime.

## 5. Módulos conceituais

1. **Context Module** — contextos organizacional e temporal
2. **Farm Entity Module** — propriedade, animal, localização
3. **Record Module** — registros anuais, mensais, diários
4. **Observation Module** — observações quantitativas e qualitativas
5. **Canonical Variable Module** — variáveis canônicas tipadas
6. **Unit Module** — unidades de medida
7. **Calculation Module** — métodos, execuções, parâmetros, resultados, GWP
8. **Software Module** — componentes e funções de software

## 6. Classes principais

Ver [`ontology/schema.py`](../ontology/schema.py) para a hierarquia completa. Destaques:

- `OrganizationalContext`, `TemporalContext`
- `AnnualPropertyInventoryRecord`, `MonthlyPropertyRecord`, `DailyAnimalProductionRecord`, `DailyAnimalNutritionRecord`
- `FeedInputObservation`, `HerdCountObservation`, `MilkProductionObservation`, `EmissionObservation`, etc.
- `EntericFermentationCH4CalculationMethod`, `TotalGHGCO2eCalculationMethod`
- `GWPParameterSet`, `CO2EquivalentResult`

## 7. Propriedades principais

**Object properties:** `hasOrganizationalContext`, `hasTemporalContext`, `observesVariable`, `hasUnit`, `hasCalculationMethod`, `implementedByFunction`, `calculatesGas`, `usesGWPParameterSet`, etc.

**Data properties:** `hasNumericValue`, `hasTextValue`, `hasCanonicalName`, `hasFunctionName`, `hasModulePath`, `hasGWP_CH4`, `hasGWP_N2O`, `hasGWP_CO2`, etc.

## 8. Variáveis canônicas

Definidas em [`ontology/catalogs.py`](../ontology/catalogs.py) e classificadas via [`ontology/mappings.py`](../ontology/mappings.py).

Cada variável canônica é um indivíduo OWL com:

- `hasCanonicalName`
- `hasDisplayName`
- `hasOriginalColumnName`
- tipo (`FeedVariable`, `HerdVariable`, etc.)

## 9. Como observações são criadas

Para cada coluna de dado relevante em uma linha CSV/DataFrame:

1. Resolver variável canônica (com resolução de ambiguidade para `total` via `layout_name`)
2. Selecionar classe de observação (`get_observation_class_for_variable`)
3. Atribuir unidade esperada (`get_expected_unit_for_variable`)
4. Criar `QuantitativeObservation` (numérico) ou `QualitativeObservation` (texto)
5. Ligar a registro, contextos e variável canônica

**Valores zero (`0`, `0.0`) não são ignorados** — zero é dado válido.

## 10. Contextos organizacional e temporal

Colunas especiais por linha:

- `_organizational_context` — JSON, ex.: `{"granularity":"property","identifier":"BR – 1"}`
- `_temporal_context` — JSON, ex.: `{"type":"interval","start":"2026-01-01","end":"2026-12-31","granularity":"year"}`

O parser aceita `date` ou `value` em contextos `instant` (compatibilidade wrappers vs exemplos).

## 11. Como cálculos são representados

Indivíduos de `CalculationMethod` ligados a:

- `hasFunctionName`, `hasModulePath`
- `requiresInputVariable`
- `calculatesGas`, `calculatesEmissionSource` (quando aplicável)
- `implementedInSoftwareComponent`

Exemplo: `calculate_enteric_fermentation_ch4` → `emissions/enteric_fermentation.py`.

## 12. Como GWP é tratado como parâmetro

O método `calculate_total_ghg_co2e`:

- possui `requiresGWPParameterSet = true`
- liga `usesGWPParameterSet` a um indivíduo `GWPParameterSet`
- **não fixa valores GWP no código da ontologia**

Exemplo injetável: `gwp_set_example_2026` com `hasGWP_CO2 = 1.0`; CH4/N2O devem ser fornecidos pelo chamador em runtime.

## 13. Como exportar a ontologia

```python
from ontology import build_full_ontology, populate_from_csv, export_ontology

onto = build_full_ontology()
populate_from_csv(onto, "dados.csv", layout_name="annual_inventory")

export_ontology(onto, "artifacts/ontology/agromrv_lite.owl", format="rdfxml")
export_ontology(onto, "artifacts/ontology/agromrv_lite.ttl", format="turtle")
```

Ou:

```bash
python -m ontology.examples
```

## 14. Como rodar os testes

```bash
pip install -e ".[dev]"
pytest
```

## 15. Como adicionar uma nova variável canônica

1. Adicionar entrada em `VARIABLE_CLASS_MAP` em [`ontology/mappings.py`](../ontology/mappings.py)
2. Mapear classe de observação em `VARIABLE_TO_OBSERVATION`
3. Definir unidade em `UNIT_RULES`
4. A variável aparecerá automaticamente em `CANONICAL_VARIABLES` via `_var_entries()`
5. Rodar `pytest tests/test_ontology_catalogs.py`

## 16. Como adicionar um novo método de cálculo

1. Adicionar entrada em `CALCULATION_METHODS` em [`ontology/catalogs.py`](../ontology/catalogs.py)
2. Criar classe correspondente em `schema.py` se necessário
3. Adicionar componente de software em `SOFTWARE_COMPONENTS`
4. Rodar `pytest tests/test_ontology_calculation_catalog.py`

## 17. Limitações

- Sem raciocínio OWL complexo (SWRL/SPARQL reasoning) nesta versão
- Restrições estruturais complementadas por validação Python em `validators.py`
- Campo `total` é ambíguo — requer `layout_name` para resolução correta
- Variáveis de resultado intermediário (`enteric_ch4`, etc.) referenciadas no catálogo de totalização podem não existir como variáveis canônicas de entrada
- Sem proveniência PROV nem integração blockchain
- Export Turtle via conversão RDF/XML → rdflib

## 18. Extensões futuras

- Integração com traceability-service (proveniência interna)
- Execuções de cálculo instanciadas (`EmissionCalculationExecution`) a partir de resultados reais
- SHACL ou validação OWL mais rigorosa
- Import opcional de vocabulários externos quando necessário
- API REST para consulta SPARQL
- Sincronização bidirecional com ontologia legada do monorepo
