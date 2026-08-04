# Visão geral da arquitetura

Protótipo modular em **processo único**. O Dash (`frontend/main.py`) é a interface e a camada que orquestra a sequência das etapas via `local_orchestrator`, chamando módulos especializados por import Python (`services/*_adapter.py`).

Não há comunicação HTTP entre o frontend e os módulos da pipeline. O FastAPI do traceability-service existe como superfície opcional/standalone e **não** é usado pelo caminho Dash.

```text
Usuário → Dash (páginas/callbacks)
        → local_orchestrator
        → adapters
        → save-file | wrappers | ontology | calculation | provenance | blockchain
        → cycle JSON + SQLite + filesystem
```

Ver também: [ADR-001](../decisions/ADR-001-frontend-as-interface-and-orchestrator.md), [ADR-002](../decisions/ADR-002-in-process-modular-integration.md).
