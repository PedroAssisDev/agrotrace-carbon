# Manual de instalação, execução e reprodução — AgroMRV-Flow

Este manual orienta um avaliador tecnicamente capacitado a instalar, executar e
reproduzir os procedimentos da avaliação da arquitetura **AgroMRV-Flow**
(repositório técnico `agrotrace-carbon`).

---

## 1. Identidade e escopo

| Nome | Uso |
|------|-----|
| **AgroMRV-Flow** | Nome canônico da arquitetura (dissertação e interface) |
| **agrotrace-carbon** | Nome do repositório e das pastas/pacotes Python |
| **CarbonSECO** | Linhagem do módulo de treinamento (`carbonseco-model-training-service`) |
| **AgroMRV-Lite** | Ontologia de trabalho (`agromrv-o-lite`) |

A avaliação usa **dois grupos** de dados: simulados (`FARM-*`) e Embrapa
(`P-*` mensal, `BR-*` anual). Dados diários estão fora do escopo da avaliação.

---

## 2. Pré-requisitos

- Python **3.11+** (desenvolvimento validado em 3.13; declare a versão usada)
- Git
- (Opcional) Foundry/Forge — apenas contratos Solidity
- Sistema operacional: Windows 10+ (PowerShell) ou Linux/macOS (bash)

---

## 3. Instalação

**Entrega segura:** use `git clone` ou o pacote gerado por
`python tooling/build_software_release.py`. **Não** copie a pasta de trabalho
do autor (pode conter `.env` com credenciais, bancos e virtualenvs).

```bash
git clone <url-do-repositorio> agrotrace-carbon
cd agrotrace-carbon
python -m venv .venv
# Windows:
.venv\Scripts\activate
.\tooling\install-workspace.ps1
# Linux/macOS:
# source .venv/bin/activate
# ./tooling/install-workspace.sh
cp .env.example .env
pip check
```

O instalador coloca os oito módulos em modo editável, incluindo extras de teste
(`pytest` via `frontend[dev]`).

---

## 4. Configuração

Edite `.env` apenas se necessário. Defaults seguros:

| Variável | Default | Notas |
|----------|---------|-------|
| `AGROTRACE_DATA_ROOT` | `frontend/data/` | Artefatos operacionais (gitignored) |
| `BLOCKCHAIN_DEFAULT_NETWORK_CODE` | `local_simulated` | **Não exige credenciais** |
| `AGROTRACE_DASH_DEBUG` | desligado | Use `1` só em desenvolvimento |
| `BLOCKCHAIN_ABI_CHECKSUM_SHA256` | preenchido no exemplo | Validação da ABI versionada |

Ancoragem Sepolia/Anvil é **opcional** e exige RPC + chave + endereço de contrato
no `.env` local — nunca versionado.

---

## 5. Preparação dos dados experimentais

### Grupo 1 — Simulados

Gerados automaticamente no seed (`--seed 42`). Determinísticos.

### Grupo 2 — Embrapa

CSVs-fonte versionados em `agrotrace-carbon-save-file/data/embrapa/`.
O seed chama `split.py` automaticamente. Detalhes e termos:
[data/embrapa/README.md](../../agrotrace-carbon-save-file/data/embrapa/README.md).

---

## 6. Seed (carga)

```bash
cd frontend
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo
```

Operação **destrutiva**. Contagem esperada: **453** ciclos
(17 + 386 + 50). Status: pendentes de aprovação; blockchain bloqueado.

Ver também [docs/development/reset-and-seed.md](../development/reset-and-seed.md).

---

## 7. Execução da aplicação

```bash
cd frontend
python main.py
# http://127.0.0.1:8050
```

Encerrar: Ctrl+C. Dados persistem em `$AGROTRACE_DATA_ROOT`.

---

## 8. Guia das 8 rotas

| Rota | Função |
|------|--------|
| `/` | Painel executivo |
| `/data-entry` | Cadastro e upload CSV |
| `/calculations` | Detalhe de cálculos (fatores IPCC AR4 / ECOFARM-T1-DAIRY) |
| `/approval` | Revisão e aprovação humana |
| `/indicators` | Análise geral |
| `/previsoes` | Inferência (após retreino local; modelos não vêm no clone) |
| `/technical-audit` | Auditoria (9 abas) |
| `/settings` | Diagnóstico técnico (não é fluxo MRV) |

---

## 9. Consultas de proveniência (interação estruturada)

Em **Auditoria Técnica → Consultas de Proveniência**:

- 13 templates SQL parametrizados (`provenance_query_templates.py`)
- Apenas `SELECT`/`WITH`; SQLite somente leitura
- Não é LLM nem chat — é *consulta estruturada* sobre o ledger

---

## 10. Aprovação e publicação

```bash
cd frontend
python scripts/approve_all_pending_cycles.py --dry-run
python scripts/approve_all_pending_cycles.py --confirm --property-prefix FARM-
```

Fluxo: revisão → aprovação → publicação final → evidências → ancoragem
(`local_simulated` por padrão) → verificação local.

---

## 11. Verificação de evidências e integridade

- SHA-256 do original (save-file)
- Pacote canônico + Merkle (blockchain-service)
- Idempotência: `SHA-256(network_code:package_hash)`
- Verificação off-chain: recomputação local de hashes
- Com `local_simulated`, a ancoragem **não** é prova on-chain

Ver [docs/limitations.md](../limitations.md).

---

## 12. Ancoragem opcional (EVM)

- `anvil_local`: Foundry Anvil + endereço de contrato
- `ethereum_sepolia`: RPC + chave + contrato
- Evidência histórica declarada: `agrotrace-carbon-blockchain-service/evidence/sepolia/`
  (ver `evidence/README.md`)

---

## 13. Previsões

Modelos **não** são versionados. Após seed/aprovação, retreine pela UI
(`/previsoes`) ou pela API do `model-training-service`; artefatos vão para
`configs/artifacts/` e `artifacts/active_models.json` (gitignored).
`random_state: 42` em `configs/training.yaml`. LSTM desabilitado.

---

## 14. Reprodução da avaliação

```bash
# Relatório em arquivo temporário (não sobrescreve evidência versionada)
python frontend/scripts/run_full_regression.py

# Publicar evidência Cap. 5
python frontend/scripts/run_full_regression.py --out docs/audits/current/regressao.json
```

Fonte semântica RF/RNF/CE: `docs/audits/current/09-resultados.json`.
Cenários CE1–CE5: `docs/academic/evaluation-scenarios.md`.

---

## 15. Limitações

Leia integralmente [docs/limitations.md](../limitations.md). Destaques:

- Ancoragem default é simulada
- Solo/estoque de carbono não implementado
- Classe `Lot` ausente na OWL
- GWP: IPCC AR4 (CH₄=25, N₂O=298)

---

## 16. Solução de problemas

| Sintoma | Ação |
|---------|------|
| Instalador PowerShell falha | Use a versão corrigida (≥ este commit); condição `Test-Path` parentetizada |
| Embrapa com 0 ciclos | Seed deve rodar `split.py`; se falhar, mensagem explícita |
| `/previsoes` vazio | Retreine modelos (não vêm no clone); confira `configs/artifacts/` |
| `provenance.emit.failed` | Com `ALLOW_MOCK_FALLBACK=False`, a falha propaga — ver logs |
| ModuleNotFoundError | Reexecute `install-workspace` no venv ativo |
| Pasta ZIP com `.env` | Use clone ou `build_software_release.py` |

---

## 17. Licenças e distribuição

- Software: [LICENSE](../../LICENSE) (uso acadêmico)
- Dados Embrapa: termos em [data/embrapa/README.md](../../agrotrace-carbon-save-file/data/embrapa/README.md)
- Evidência Sepolia: [evidence/README.md](../../agrotrace-carbon-blockchain-service/evidence/README.md)

### Pacote limpo

```bash
python tooling/build_software_release.py
# Gera software-release/ sem .env, DBs, .venv
```
