# AgroTrace Carbon

Protótipo acadêmico de plataforma MRV (Monitoring, Reporting, Verification) para dados agropecuários e emissões de GEE.

## Problema

Rastrear, de ponta a ponta, o ciclo de vida de dados de fazenda — do arquivo bruto à evidência criptográfica — com aprovação humana antes de qualquer ancoragem.

## Escopo

- Ingestão e preservação de arquivos
- Normalização por layouts (intraday / monthly / annual)
- Ontologia AgroMRV-O Lite
- Cálculos de emissão (IPCC/ECOFARM)
- Revisão e aprovação por cálculo
- Publicação de manifesto final
- Proveniência append-only
- Pacote de evidências, Merkle Root e ancoragem **simulada**

## Arquitetura

Protótipo modular executado em **processo único**. O frontend Dash atua como **interface e camada de orquestração**; módulos especializados encapsulam as responsabilidades técnicas da pipeline. A integração é por **chamadas Python diretas** (sem HTTP entre módulos).

| Módulo | Responsabilidade |
|--------|------------------|
| `agrotrace-carbon-save-file` | Arquivo original + hash SHA-256 |
| `agrotrace-carbon-wrappers-service` | Transformação e normalização |
| `agrotrace-carbon-ontology-manager` | Ontologia, validação semântica |
| `agrotrace-carbon-calculation-service` | Fórmulas e resultados de emissão |
| `agrotrace-carbon-traceability-service` | Ledger de proveniência (UoW Python; FastAPI opcional standalone) |
| `agrotrace-carbon-blockchain-service` | Evidências, Merkle, âncora simulada, verificação |
| `frontend` | UI + orquestração (`local_orchestrator`) |

## Pipeline oficial

```text
Upload → preservação → proveniência inicial → wrapper → normalizado
→ ontologia → validação semântica → cálculo preliminar
→ revisão por item → aprovação geral → publicação (manifesto)
→ evidências → Merkle → ancoragem simulada → verificação
```

Blockchain só após a publicação final aprovada.

## Requisitos

- Python 3.10+
- Dependências dos módulos (ver `requirements.txt` / `pyproject.toml` de cada serviço)
- Ambiente virtual recomendado na raiz do workspace

## Preparação e execução

```bash
# na raiz (venv recomendado)
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r frontend/requirements.txt

# opcional, para pipeline completa sem fallback:
# pip install -e agrotrace-carbon-traceability-service
# pip install -e agrotrace-carbon-blockchain-service
# pip install -e agrotrace-carbon-ontology-manager
# pip install -e agrotrace-carbon-calculation-service

cd frontend
python main.py
# UI: http://127.0.0.1:8050
```



Scripts de seed/smoke e demais comandos: [frontend/README.md](frontend/README.md).

## Dados locais

| Caminho | Conteúdo |
|---------|----------|
| `frontend/data/cycles/` | Estado operacional dos ciclos (JSON) |
| `frontend/data/publications/` | Manifestos finais |
| `frontend/data/db/` | SQLite proveniência e blockchain |
| `frontend/data/normalized/` | Lotes normalizados |
| `frontend/data/evidence_packages/` | Pacotes de evidência |
| `agrotrace-carbon-save-file/data/originals/` | Arquivos brutos preservados |

## Limitações do protótipo

- Processo único (não é malha de microsserviços)
- SQLite e filesystem locais (MVP)
- Ancoragem blockchain simulada (não há rede pública)
- Granularidade `lot` em metadados; ontologia OWL atual modela Property/Animal

## Documentação

Índice completo: [docs/README.md](docs/README.md)
