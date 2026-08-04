# Solução de problemas

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| Conflito de import com o pacote `app` | Uso de `frontend/app.py` como entrypoint | Use `frontend/main.py` como entrypoint |
| Serviços não encontrados no import | `sys.path` sem os pacotes irmãos | Rode via `frontend/main.py` (o bootstrap ajusta o `sys.path`) |
| UI carrega mas dados vazios | `AGROTRACE_DATA_ROOT` sem seed | Rode `seed_test_scenarios.py` (ver [reset-and-seed.md](reset-and-seed.md)) |
| Fallback mock aparecendo | `ALLOW_MOCK_FALLBACK`/`USE_MOCK_DATA` ligados | Confira [configuration.md](configuration.md); o fluxo real usa chamadas diretas |
| `forge` não encontrado | Foundry ausente | Instale o Foundry ou use `--skip-forge` na regressão |
| Ancoragem exige chave privada | Provider EVM selecionado | Use `local_simulated` (padrão) ou configure o `.env` local |

Bancos SQLite são inicializados pelo bootstrap sob `AGROTRACE_DATA_ROOT/db/`. Não apague
dados operacionais para "resolver" um problema sem antes ler
[data-directories.md](data-directories.md).
