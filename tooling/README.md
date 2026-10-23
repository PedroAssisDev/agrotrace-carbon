# Tooling do monorepo AgroMRV-Flow (agrotrace-carbon)

## O que é

Pasta de **manutenção do workspace**: atalhos para instalar, testar e empacotar
os oito serviços + o frontend **juntos**.

## O que não é

- **Não** faz parte do ciclo MRV (upload → cálculo → aprovação → blockchain).
- **Não** é a pasta de operação do protótipo. Seed, aprovação em massa,
  `validate_*`, smoke e regressão completa ficam em `frontend/scripts/`.
- **Não** substitui a UI Dash (`frontend/main.py`).

## Por que existe

O repositório é um monorepo: cada serviço tem o próprio `pyproject.toml` e
precisa ser instalado no mesmo venv para a UI e a regressão funcionarem
(`rdflib`, `pydantic-settings`, `structlog`, etc.).

Sem esta pasta, quem clona o repo teria que:

1. Entrar em cada uma das 8 pastas e rodar `pip install -e .` (com extras certos)
2. Lembrar a ordem e os filtros dos testes de cada serviço
3. Copiar manualmente o que entra no pacote de entrega `software-release/`

Com `tooling/`, isso vira poucos comandos na **raiz do repositório**, com o
venv já ativado.

## Quando usar

| Situação | Comando |
|----------|---------|
| Acabou de clonar / criou venv novo / faltam deps | `.\tooling\install-workspace.ps1` (ou `.sh`) |
| Quer checar rápido se os serviços ainda passam | `.\tooling\test-workspace.ps1` (ou `.sh`) |
| Vai entregar o pacote limpo de software | `python tooling/build_software_release.py` |
| Quer garantir que não voltou código legado no runtime | `python tooling/verify_no_active_legacy.py` |

No dia a dia do protótipo (carregar dados, aprovar ciclos, abrir a UI, regressão
completa) use `frontend/scripts/` — não precisa desta pasta.

Seed canônico e aprovação em massa: ver
[`../docs/development/reset-and-seed.md`](../docs/development/reset-and-seed.md).
Instalação detalhada: [`../docs/development/setup.md`](../docs/development/setup.md).

## Pré-requisitos

- Estar na **raiz** do repositório (`agrotrace-carbon/`)
- Venv ativado (ex.: `.venv\Scripts\activate` no Windows)
- Python 3.11+ (conforme README raiz)

## Scripts

### `install-workspace.ps1` / `install-workspace.sh`

Instala em modo editável (`pip install -e`) os oito projetos e o frontend no
ambiente Python ativo, incluindo extras de teste/dev onde aplicável, e roda
`pip check`.

```powershell
# Windows
.\tooling\install-workspace.ps1
```

```bash
# Linux / macOS
./tooling/install-workspace.sh
```

Use depois de criar o venv, ou quando a regressão falhar com
`ModuleNotFoundError` (`rdflib`, `pydantic_settings`, `sklearn`, etc.).

### `test-workspace.ps1` / `test-workspace.sh`

1. Roda `verify_no_active_legacy.py` (aviso se houver marcadores)
2. Executa a suíte de testes de cada serviço
3. Executa os testes do frontend

Não altera `frontend/data/` operacional. É mais leve que a regressão completa
(`frontend/scripts/run_full_regression.py`).

```powershell
.\tooling\test-workspace.ps1
```

```bash
./tooling/test-workspace.sh
```

### `build_software_release.py`

Gera a pasta local `software-release/` (gitignored): cópia limpa do software
para entrega/submissão, **sem** `academic-evidence/`, bancos SQLite, caches,
`.venv` ou `.env`.

```bash
python tooling/build_software_release.py
```

A pasta gerada pode ser apagada e recriada a qualquer momento.

### `verify_no_active_legacy.py`

Varre o código de produção dos oito projetos + frontend e falha se encontrar
mecanismos legados (ex.: `TemporalScope.YEARLY`, `process_file_auto` ativo).
Ignora testes, `frontend/scripts/`, docs históricos e esta pasta `tooling/`.

```bash
python tooling/verify_no_active_legacy.py
```

## Relação com outras pastas

| Pasta | Papel |
|-------|--------|
| `tooling/` | Install / test / release / legado do **monorepo** |
| `frontend/scripts/` | Seed, Embrapa, aprovação, `validate_*`, regressão da **aplicação** |
| `software-release/` | Saída gerada pelo builder (não versionar) |
| `academic-evidence/` | Evidências históricas da dissertação (fora do runtime) |

## Ver também

- [README raiz](../README.md) — instalação e fluxo de demo
- [docs/development/testing.md](../docs/development/testing.md) — regressão canônica
