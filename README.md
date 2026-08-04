# AgroTrace Carbon

Protótipo acadêmico da arquitetura proposta para MRV agropecuário (Monitoring,
Reporting, Verification). Cobre o ciclo de vida auditável do dado — do arquivo bruto à
verificação de evidência — com aprovação humana antes de qualquer ancoragem.

## Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `frontend` | Interface Dash e orquestração (8 rotas) |
| `agrotrace-carbon-save-file` | Preservação do original + SHA-256 |
| `agrotrace-carbon-wrappers-service` | Normalização por layouts |
| `agrotrace-carbon-ontology-manager` | Ontologia de trabalho/final e validação |
| `agrotrace-carbon-calculation-service` | Cálculo de emissões (IPCC/ECOFARM) |
| `agrotrace-carbon-model-training-service` | Estimativa preditiva |
| `agrotrace-carbon-traceability-service` | Serviço de proveniência |
| `agrotrace-carbon-blockchain-service` | Evidências, Merkle e ancoragem |

Integração por chamadas Python diretas (sem HTTP entre módulos). Ancoragem com provider
simulado por padrão (`local_simulated`) e provider EVM opcional (Anvil/Sepolia). A
blockchain só age após `FINAL_ONTOLOGY_PUBLISHED`.

## Requisitos mínimos

- Python 3.11+
- (Opcional) Foundry/Forge para os contratos Solidity

## Instalação e configuração

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r frontend/requirements.txt
pip install -r agrotrace-carbon-wrappers-service/requirements.txt
cp .env.example .env   # ajuste local; nunca versione .env
```

## Executar o frontend

```bash
cd frontend
python main.py
# UI: http://127.0.0.1:8050
```

## Regressão completa

```bash
python frontend/scripts/run_full_regression.py
```

## Dados operacionais

Ciclos, bancos SQLite, ontologias publicadas e pacotes de evidência ficam sob
`AGROTRACE_DATA_ROOT` (padrão `frontend/data/`), ignorado pelo Git. Não versione nem
apague esses dados manualmente.

## Documentação e dissertação

- Índice da documentação: [docs/README.md](docs/README.md)
- Alinhamento com a dissertação: [docs/academic/dissertation-alignment.md](docs/academic/dissertation-alignment.md)
  (o PDF/LaTeX da dissertação não está versionado neste repositório)

## Licença

Uso acadêmico. Consulte o autor antes de redistribuir.
