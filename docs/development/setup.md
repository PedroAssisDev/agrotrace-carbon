# Instalação e execução

## Requisitos mínimos

- Python 3.11+
- (Opcional, para providers EVM) Foundry/Forge para os contratos Solidity.

## Instalação

Instale as dependências do frontend e dos serviços usados pelo caminho Dash:

```bash
pip install -r frontend/requirements.txt
pip install -r agrotrace-carbon-wrappers-service/requirements.txt
```

Os pacotes irmãos são adicionados ao `sys.path` pelo bootstrap
(`frontend/services/bootstrap`), que também inicializa os SQLite sob
`AGROTRACE_DATA_ROOT/db/`.

## Configuração inicial

Copie o exemplo de variáveis de ambiente e ajuste localmente (nunca versione `.env`):

```bash
cp .env.example .env
```

Detalhes das flags e variáveis em [configuration.md](configuration.md) e
[data-directories.md](data-directories.md).

## Executar o frontend

```bash
cd frontend
python main.py
```

UI em `http://127.0.0.1:8050`.

## Rotas canônicas (8)

`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`,
`/technical-audit`, `/settings`.

Rotas antigas são redirecionadas por `rotas canônicas` em `frontend/pages/router.py`.

## Próximos passos

- Reset e seed de dados de teste: [reset-and-seed.md](reset-and-seed.md).
- Testes e regressão: [testing.md](testing.md) e [validation-scripts.md](validation-scripts.md).
- Problemas comuns: [troubleshooting.md](troubleshooting.md).
