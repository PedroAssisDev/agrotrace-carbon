# Executar o protótipo

```bash
cd frontend
python main.py
```

UI em `http://127.0.0.1:8050`.

Rotas ativas: `/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/technical-audit`, `/settings`.

O bootstrap (`services.bootstrap`) adiciona os pacotes irmãos ao `sys.path` e inicializa os SQLite sob `frontend/data/db/`.
