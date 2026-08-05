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
pip install -e agrotrace-carbon-ontology-manager
pip install -e "agrotrace-carbon-blockchain-service[dev]"
pip install -e "agrotrace-carbon-traceability-service[dev]"
pip install -e "agrotrace-carbon-model-training-service[dev]"
pip install -e "frontend[dev]"
cp .env.example .env   # ajuste local; nunca versione .env
```

## Executar o frontend

```bash
cd frontend
python main.py
# UI: http://127.0.0.1:8050
```

## Regressão completa

Valida o monorepo de ponta a ponta sob um `AGROTRACE_DATA_ROOT` temporário
(não altera os dados operacionais em `frontend/data/`). Executa testes dos
serviços, Forge (contratos), testes do frontend, todos os `validate_*.py`,
smoke, ciclo completo de emissão e varredura de segredos; gera
`docs/audits/current/regressao.json`.

É a verificação canônica antes de submissão ou após mudanças amplas: confirma
que packaging, pipeline, gate blockchain e validadores ainda passam juntos.

```bash
python frontend/scripts/run_full_regression.py
# Mais rápido (pula smoke/ciclo completo):  ... --quick
# Sem contratos Solidity:                  ... --skip-forge
```

## Dados de demonstração (simulados + Embrapa)

Operação **destrutiva**: apaga ciclos/DBs locais e reimporta. Exige `--confirm`.

```bash
cd frontend

# Fluxo completo: wipe → simulados (FARM-*) → Embrapa monthly (P-*) + annual (BR-*)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo

# Só simulados (não carrega pastas Embrapa)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --skip-embrapa

# Ano dos inventários anuais Embrapa (default: 2022)
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --embrapa-year 2022
```

| Flag | Função |
|------|--------|
| `--confirm` | Obrigatório; sem ele o script aborta |
| `--seed` | Semente RNG dos CSVs simulados (default `42`) — mesma semente ⇒ mesmos dados |
| `--profile demo\|full` | `demo` = 17 entradas/ciclos (padrão); `full` = perfis extras |
| `--skip-embrapa` | Não importa Embrapa; só FARM-* |
| `--embrapa-year` | Ano dos anuais BR-* (default `2022`) |

Status esperado dos ciclos após o seed: pendentes de aprovação (blockchain ainda bloqueado).

## Aprovação em massa

Avança cada ciclo pendente: revisão → aprovação → publicação final → evidências → blockchain.
Também exige `--confirm` (exceto em dry-run).

```bash
cd frontend

# Ver o que seria aprovado (não altera dados)
python scripts/approve_all_pending_cycles.py --dry-run

# Aprovar todos os pendentes
python scripts/approve_all_pending_cycles.py --confirm

# Por prefixo: só simulados, só Embrapa mensal ou só anual
python scripts/approve_all_pending_cycles.py --confirm --property-prefix FARM-
python scripts/approve_all_pending_cycles.py --confirm --property-prefix P-
python scripts/approve_all_pending_cycles.py --confirm --property-prefix BR-

# Uma propriedade específica: liste no dry-run e copie um property_id
python scripts/approve_all_pending_cycles.py --dry-run
# Exemplo (simulado oficial):
python scripts/approve_all_pending_cycles.py --confirm --property-id FARM-MONTHLY-001
# Exemplo (qualquer outra do dry-run — troque pelo id listado, ex. Embrapa P-* / BR-*):
python scripts/approve_all_pending_cycles.py --confirm --property-id BR-12

# Limitar quantidade
python scripts/approve_all_pending_cycles.py --confirm --limit 10
```

| Flag | Função |
|------|--------|
| `--dry-run` | Lista ciclos sem alterar |
| `--confirm` | Executa a aprovação em massa |
| `--property-prefix` | Filtra por prefixo (`FARM-`, `P-`, `BR-`) |
| `--property-id` | Filtra por propriedade exata |
| `--limit` | Processa só N ciclos (`0` = todos) |



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
