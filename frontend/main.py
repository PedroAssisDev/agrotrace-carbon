"""
AgroTrace Carbon — Frontend Python (chamadas diretas).

Entry point: python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = FRONTEND_DIR.parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

# Carrega .env antes de ``config`` / logging, para o reloader do Dash
# (processo filho) herdar o mesmo AGROTRACE_DATA_ROOT que o pai.
try:
    from dotenv import load_dotenv

    load_dotenv(WORKSPACE_ROOT / ".env", override=False)
    load_dotenv(FRONTEND_DIR / ".env", override=False)
    # Credenciais Sepolia / Anvil tipadas ficam no .env do blockchain-service.
    load_dotenv(
        WORKSPACE_ROOT / "agrotrace-carbon-blockchain-service" / ".env",
        override=True,
    )
except ImportError:
    pass

from utils.logging_config import get_logger, setup_logging

setup_logging()

import dash
import dash_bootstrap_components as dbc
from flask import send_from_directory

import config
from config import AUTH_BACKGROUNDS_DIR, DASH_HOST, DASH_PORT, DEBUG, LOGO_DIR, ensure_data_dirs
from layout.main_layout import create_main_layout
from layout.theme import THEME
from services.bootstrap import bootstrap_all

logger = get_logger("agrotrace.app")

ensure_data_dirs()
bootstrap_result = bootstrap_all()
logger.info("Bootstrap: %s", bootstrap_result)

dash_app = dash.Dash(
    __name__,
    assets_folder=str(FRONTEND_DIR / "assets"),
    external_stylesheets=[THEME, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title=config.APP_TITLE,
)
server = dash_app.server


@server.route("/ws-assets/<path:subpath>")
def serve_workspace_assets(subpath: str):
    if subpath.startswith("auth_backgrounds/"):
        return send_from_directory(AUTH_BACKGROUNDS_DIR, subpath.split("/", 1)[1])
    if subpath.startswith("logo/"):
        return send_from_directory(LOGO_DIR, subpath.split("/", 1)[1])
    return ("Not found", 404)


dash_app.layout = create_main_layout()

from callbacks import register_callbacks  # noqa: E402 — após criação do dash_app

register_callbacks(dash_app)

if __name__ == "__main__":
    dash_app.run(host=DASH_HOST, port=DASH_PORT, debug=DEBUG)
