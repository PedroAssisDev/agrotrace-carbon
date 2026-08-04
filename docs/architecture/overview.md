# Visão geral da arquitetura

Protótipo modular em **processo único** para o ciclo de vida auditável de dados
agropecuários, emissões, proveniência e ancoragem. O frontend Dash
(`frontend/main.py`) é a interface e a camada que orquestra a sequência de etapas via
`frontend/services/local_orchestrator.py`, chamando os módulos especializados por
import Python direto através de `frontend/services/*_adapter.py`.

## Princípio de integração

Não há comunicação HTTP entre o frontend e os módulos da pipeline. A integração é feita
por chamada direta a funções/classes Python (ver
[ADR-002](decisions/ADR-002-in-process-modular-integration.md)). O FastAPI do
traceability-service existe como superfície opcional/standalone e **não** é usado pelo
caminho Dash.

```text
Usuário → Dash (páginas/callbacks)
        → local_orchestrator
        → adapters (services/*_adapter.py)
        → save-file | wrappers | ontology | calculation | model-training | traceability | blockchain
        → cycle JSON + SQLite + filesystem (AGROTRACE_DATA_ROOT)
```

## Módulos

| Módulo | Papel | Documento |
|--------|-------|-----------|
| frontend | Interface e orquestrador visual (8 rotas) | [../modules/frontend.md](../modules/frontend.md) |
| save-file | Preservação do original + SHA-256 | [../modules/save-file.md](../modules/save-file.md) |
| wrappers-service | Normalização por layouts versionados | [../modules/wrappers-service.md](../modules/wrappers-service.md) |
| ontology-manager | Ontologia de trabalho e final, validação | [../modules/ontology-manager.md](../modules/ontology-manager.md) |
| calculation-service | Cálculo de emissões (IPCC/ECOFARM) | [../modules/calculation-service.md](../modules/calculation-service.md) |
| model-training-service | Estimativa preditiva (modelos) | [../modules/model-training-service.md](../modules/model-training-service.md) |
| traceability-service | Serviço de proveniência (etapas 1–20) | [../modules/traceability-service.md](../modules/traceability-service.md) |
| blockchain-service | Evidências, Merkle e ancoragem (etapas 14–19) | [../modules/blockchain-service.md](../modules/blockchain-service.md) |

## Boundaries (limites de responsabilidade)

- O frontend **orquestra e apresenta**; não implementa regra de negócio dos serviços.
- O traceability-service **observa e registra** o ciclo (linhagem/proveniência); não
  ancora nem substitui a blockchain.
- O blockchain-service atua **apenas após** a publicação final aprovada
  (`FINAL_ONTOLOGY_PUBLISHED`); ver [ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md).
- A ancoragem tem provider **simulado por padrão** (`local_simulated`) e provider **EVM**
  (Anvil local / Sepolia); ver [security-and-integrity.md](security-and-integrity.md).

## Contexto acadêmico

O protótipo corresponde ao terceiro ciclo de desenvolvimento da pesquisa (arquitetura
proposta para MRV agropecuário). A relação com os requisitos e cenários oficiais da
dissertação está em [../academic/requirements.md](../academic/requirements.md) e
[../academic/evaluation-scenarios.md](../academic/evaluation-scenarios.md).

## Ver também

- [data-lifecycle.md](data-lifecycle.md) — ciclo de vida do dado.
- [component-responsibilities.md](component-responsibilities.md) — o que cada componente faz e não faz.
- [ADR-001](decisions/ADR-001-frontend-as-interface-and-orchestrator.md), [ADR-002](decisions/ADR-002-in-process-modular-integration.md), [ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md).
