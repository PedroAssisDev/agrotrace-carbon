# AgroMRV-Flow

Protótipo acadêmico da arquitetura **AgroMRV-Flow** para MRV agropecuário
(Monitoring, Reporting, Verification). O repositório Git chama-se
`agrotrace-carbon` (nome técnico das pastas e pacotes); a identidade acadêmica e
da interface é **AgroMRV-Flow**.

Cobre o ciclo de vida auditável do dado — do arquivo bruto à verificação de
evidência — com aprovação humana antes de qualquer ancoragem.

## Módulos (pasta → pacote → papel)

| Pasta | Pacote Python | Responsabilidade |
|--------|----------------|------------------|
| `frontend` | `agrotrace-carbon-frontend` | Interface Dash e orquestração (8 rotas) |
| `agrotrace-carbon-save-file` | `agrotrace-carbon-save-file` | Preservação do original + SHA-256 |
| `agrotrace-carbon-wrappers-service` | `agrotrace-carbon-wrappers-service` | Normalização por layouts |
| `agrotrace-carbon-ontology-manager` | `agromrv-o-lite` | Ontologia de trabalho/final e validação |
| `agrotrace-carbon-calculation-service` | `ecofarm-calculations` | Cálculo de emissões (IPCC/ECOFARM) |
| `agrotrace-carbon-model-training-service` | `carbonseco-model-training-service` | Estimativa preditiva (linhagem CarbonSECO) |
| `agrotrace-carbon-traceability-service` | `agrotrace-carbon-provenance-service` | Serviço de proveniência |
| `agrotrace-carbon-blockchain-service` | `agrotrace-carbon-blockchain-service` | Evidências, Merkle e ancoragem |

Integração por chamadas Python diretas (sem HTTP entre módulos). Ancoragem com
provider simulado por padrão (`local_simulated`) e provider EVM opcional
(Anvil/Sepolia). A blockchain só age após `FINAL_ONTOLOGY_PUBLISHED`.

A pasta [`tooling/`](tooling/README.md) concentra atalhos de manutenção do
monorepo (instalar, testar, empacotar). Não faz parte do ciclo MRV — seed,
aprovação e regressão ficam em `frontend/scripts/`.

## Requisitos mínimos

- Python 3.11+ (recomendado 3.11–3.13; desenvolvimento validado em 3.13)
- (Opcional) Foundry/Forge para os contratos Solidity

## Instalação e configuração

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
.\tooling\install-workspace.ps1   # Linux/macOS: ./tooling/install-workspace.sh
cp .env.example .env              # ajuste local; nunca versione .env
```

**Distribuição à banca:** use `git clone` ou o pacote gerado por
`python tooling/build_software_release.py`. **Não** copie a pasta de trabalho
inteira — ela pode conter `.env` local, bancos operacionais e virtualenvs.

## Executar o frontend

```bash
cd frontend
python main.py
# UI: http://127.0.0.1:8050
```

## Regressão completa

Valida o monorepo de ponta a ponta sob um `AGROTRACE_DATA_ROOT` temporário
(não altera os dados operacionais em `frontend/data/`). Por padrão grava o
relatório em um arquivo temporário; use `--out` para publicar sob
`docs/audits/current/`.

```bash
python frontend/scripts/run_full_regression.py
# Publicar evidência versionada:
python frontend/scripts/run_full_regression.py --out docs/audits/current/regressao.json
# Mais rápido (pula smoke/ciclo completo):  ... --quick
# Sem contratos Solidity:                  ... --skip-forge
```

## Dados de demonstração (dois grupos da avaliação)

A avaliação usa **dois grupos** de dados (o grupo diário está fora do escopo):

1. **Simulados (`FARM-*`)** — gerados com RNG (`--seed 42`).
2. **Embrapa** — mensal `P-*` e anual `BR-*` (CSVs-fonte versionados; o seed
   executa `split.py` automaticamente antes da importação).

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
```

## Dados operacionais

Ciclos, bancos SQLite, ontologias publicadas e pacotes de evidência ficam sob
`AGROTRACE_DATA_ROOT` (padrão `frontend/data/`), ignorado pelo Git. Não versione nem
apague esses dados manualmente.

## Documentação e dissertação

- Índice da documentação: [docs/README.md](docs/README.md)
- Alinhamento com a dissertação: [docs/academic/dissertation-alignment.md](docs/academic/dissertation-alignment.md)
- Manual de instalação e reprodução: [docs/manual/README.md](docs/manual/README.md)
- Proveniência dos dados Embrapa: [agrotrace-carbon-save-file/data/embrapa/README.md](agrotrace-carbon-save-file/data/embrapa/README.md)

## Licença

Uso acadêmico. Consulte o autor antes de redistribuir. Veja [LICENSE](LICENSE).
