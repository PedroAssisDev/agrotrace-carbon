# Instalação e execução

## Requisitos mínimos

- Python 3.11+
- (Opcional, para providers EVM) Foundry/Forge para os contratos Solidity.

## Instalação

Instale o workspace completo (recomendado — editable install dos 8 projetos):

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
.\tooling\install-workspace.ps1   # Linux/macOS: ./tooling/install-workspace.sh
```

Detalhes: [../../tooling/README.md](../../tooling/README.md).

O bootstrap (`frontend/services/bootstrap.py`) também adiciona os pacotes irmãos ao
`sys.path` e inicializa os SQLite sob `AGROTRACE_DATA_ROOT/db/`. A instalação via
tooling cobre dependências de teste/regressão que o `sys.path` sozinho não garante.

## Configuração inicial

```bash
cp .env.example .env
```

Ajuste localmente; nunca versione `.env`. Detalhes: [configuration.md](configuration.md) e
[data-directories.md](data-directories.md).

## Executar o frontend

```bash
cd frontend
python main.py
```

UI em `http://127.0.0.1:8050`. Entrypoint canônico: `frontend/main.py` (não use
`frontend/app.py` — conflita com o pacote `app` do blockchain-service).

## Rotas canônicas (8)

| Rota | Tela |
|------|------|
| `/` | Painel Executivo |
| `/data-entry` | Entrada de Dados |
| `/calculations` | Cálculos de Emissão |
| `/approval` | Revisão e Aprovação |
| `/indicators` | Análise Geral |
| `/previsoes` | Previsões |
| `/technical-audit` | Auditoria Técnica |
| `/settings` | Configurações |

Paths desconhecidos caem no Painel Executivo. Não há mecanismo de redirect de rotas
legadas em `router.py`.

## Próximos passos

- Reset e seed: [reset-and-seed.md](reset-and-seed.md).
- Testes: [testing.md](testing.md) e [validation-scripts.md](validation-scripts.md).
- Limitações: [../limitations.md](../limitations.md).
- Problemas comuns: [troubleshooting.md](troubleshooting.md).
