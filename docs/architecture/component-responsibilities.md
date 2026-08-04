# Responsabilidades dos componentes

Para cada componente: o que recebe, o que produz, onde persiste e o que **não** faz.
O contrato de integração com o frontend é sempre por import Python direto (adapters).

| Componente | Recebe | Produz | Persistência | Não faz |
|------------|--------|--------|--------------|---------|
| frontend | Ações do usuário | Estado do ciclo, telas | `cycles/*.json` | Regra de negócio dos serviços |
| save-file | Arquivo bruto | Original preservado + SHA-256 | `save-file/data/originals/` | Normalização/cálculo |
| wrappers-service | Original + layout | Lote normalizado | `frontend/data/normalized/` | Cálculo/ontologia |
| ontology-manager | Dados normalizados | Ontologia de trabalho/final (OWL/TTL) | `frontend/data/ontology_exports/` | Cálculo/ancoragem |
| calculation-service | Dados de fazenda/período | Emissões CO₂e (preliminar) | via ciclo/ontologia | Publicação/ancoragem |
| model-training-service | Séries/exemplos | Estimativa preditiva | `artifacts/` | Substituir cálculo oficial |
| traceability-service | Eventos de etapa | Ledger de proveniência | `db/provenance.db` | Ancoragem blockchain |
| blockchain-service | Manifesto publicado | Pacote, Merkle Root, âncora, verificação | `db/blockchain_service.db` | Executar antes do gate |

## Contratos principais com o frontend

| Pacote | Símbolos |
|--------|----------|
| save-file | `save_original_file`, `save_original_content` |
| wrappers | `process_file` |
| ontology-manager | `build_full_ontology`, `populate_from_dataframe`, `validate_all`, `export_ontology` |
| calculation-service | `compute_farm_period_emissions`, `FarmPeriodInput`, `gwp_ipcc_ar4` |
| traceability-service | `ProvenanceRecorder`, `get_uow_factory` |
| blockchain-service | use cases observe / build evidence / anchor / verify |

## Frontend interno

- Páginas em `frontend/pages/`, callbacks em `frontend/callbacks/`.
- Adapters e view services em `frontend/services/`.
- Orquestração em `local_orchestrator.py`; estado em `cycle_state.py`.

Detalhes por módulo em [../modules/](../modules/). Estado dos resultados em
[result-state-model.md](result-state-model.md).
