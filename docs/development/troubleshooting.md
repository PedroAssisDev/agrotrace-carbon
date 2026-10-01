# Solução de problemas

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| Conflito de import com o pacote `app` | Uso de `frontend/app.py` como entrypoint | Use `frontend/main.py` como entrypoint |
| Serviços não encontrados no import | `sys.path` sem os pacotes irmãos | Rode via `frontend/main.py` (o bootstrap ajusta o `sys.path`) |
| UI carrega mas dados vazios | `AGROTRACE_DATA_ROOT` sem seed | Rode `reset_and_seed_pending_cycles.py --confirm` (ver [reset-and-seed.md](reset-and-seed.md)) |
| Serviços faltam deps | Só `sys.path`, sem install | Rode `tooling/install-workspace.ps1` (ou `.sh`) |
| Fallback mock aparecendo | `ALLOW_MOCK_FALLBACK`/`USE_MOCK_DATA` ligados | Confira [configuration.md](configuration.md); o fluxo real usa chamadas diretas |
| Rota antiga não redireciona | `LEGACY_REDIRECTS` removido | Use as 8 rotas canônicas ([setup.md](setup.md)) |
| `forge` não encontrado | Foundry ausente | Instale o Foundry ou use `--skip-forge` na regressão |
| Ancoragem exige chave privada | Provider EVM selecionado | Use `local_simulated` (padrão) ou configure o `.env` local |

Bancos SQLite são inicializados pelo bootstrap sob `AGROTRACE_DATA_ROOT/db/`. Não apague
dados operacionais para "resolver" um problema sem antes ler
[data-directories.md](data-directories.md).
