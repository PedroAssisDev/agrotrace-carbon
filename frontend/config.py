"""Configuração central do frontend AgroTrace Carbon.

Único módulo autorizado a ler ``AGROTRACE_DATA_ROOT``. Quando a variável está
ausente, preserva o layout histórico sob ``frontend/data`` e originais no
serviço save-file. Quando definida, todos os artefatos operacionais passam a
ser gravados sob esse diretório.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Diretórios fixos do workspace ────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = FRONTEND_DIR.parent

# Serviços existentes (somente leitura/import de código)
SAVE_FILE_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-save-file"
WRAPPERS_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-wrappers-service"
CALCULATION_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-calculation-service"
ONTOLOGY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-ontology-manager"
BLOCKCHAIN_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-blockchain-service"
TRACEABILITY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-traceability-service"
TRACEABILITY_SRC_DIR = TRACEABILITY_SERVICE_DIR / "src"
MODEL_TRAINING_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-model-training-service"
MODEL_TRAINING_CONFIG_PATH = MODEL_TRAINING_SERVICE_DIR / "configs" / "training.yaml"
MODEL_TRAINING_SRC_DIR = MODEL_TRAINING_SERVICE_DIR / "src"
_DEFAULT_MODEL_TRAINING_ARTIFACTS = MODEL_TRAINING_SERVICE_DIR / "artifacts"
# Placeholders — preenchidos por _apply_resolved_root
MODEL_TRAINING_ARTIFACTS_DIR: Path
MODEL_REGISTRY_PATH: Path
MODEL_TRAINING_PROCESSED_DIR: Path

# Assets do workspace (referência, sem mover)
AUTH_BACKGROUNDS_DIR = WORKSPACE_ROOT / "auth_backgrounds"
LOGO_DIR = WORKSPACE_ROOT / "logo"
LOGO_PATH = LOGO_DIR / "Logo.png"

# CSV de exemplo no workspace (inputs, não artefato operacional)
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "data"

# Embrapa datasets (leitura; permanecem no serviço save-file)
SAVE_FILE_EMBRAPA_DIR = SAVE_FILE_SERVICE_DIR / "data" / "embrapa"
SAVE_FILE_EMBRAPA_MONTHLY_DIR = SAVE_FILE_EMBRAPA_DIR / "monthly"
SAVE_FILE_EMBRAPA_ANNUAL_DIR = SAVE_FILE_EMBRAPA_DIR / "annual"

_DATA_ROOT_ENV = "AGROTRACE_DATA_ROOT"
_DEFAULT_DATA_DIR = FRONTEND_DIR / "data"
_DEFAULT_SAVE_ORIGINALS = SAVE_FILE_SERVICE_DIR / "data" / "originals"
_DEFAULT_SAVE_EMULATED = SAVE_FILE_SERVICE_DIR / "data" / "emulated_uploads"

# Placeholders — preenchidos por _apply_resolved_root abaixo
DATA_DIR: Path
RAW_ORIGINALS_DIR: Path
NORMALIZED_DIR: Path
ONTOLOGY_DIR: Path
ONTOLOGY_EXPORTS_DIR: Path
EVIDENCE_PACKAGES_DIR: Path
PUBLICATIONS_DIR: Path
REPORTS_DIR: Path
CYCLES_DIR: Path
PROPERTIES_DIR: Path
DB_DIR: Path
LOGS_DIR: Path
PROV_DB_PATH: Path
BLOCKCHAIN_DB_PATH: Path
SAVE_FILE_ORIGINALS_DIR: Path
SAVE_FILE_EMULATED_UPLOADS_DIR: Path
_CUSTOM_DATA_ROOT: Path | None = None


def _resolve_env_data_root() -> Path | None:
    raw = os.environ.get(_DATA_ROOT_ENV, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def get_data_root() -> Path:
    """Retorna o diretório efetivo de artefatos operacionais."""
    return DATA_DIR


def is_custom_data_root() -> bool:
    """True quando AGROTRACE_DATA_ROOT (ou apply_data_root) está ativo."""
    return _CUSTOM_DATA_ROOT is not None


def _apply_resolved_root(root: Path | None) -> None:
    """Atualiza constantes de path derivadas do data root efetivo."""
    global DATA_DIR, RAW_ORIGINALS_DIR, NORMALIZED_DIR, ONTOLOGY_DIR
    global ONTOLOGY_EXPORTS_DIR, EVIDENCE_PACKAGES_DIR, PUBLICATIONS_DIR
    global REPORTS_DIR, CYCLES_DIR, PROPERTIES_DIR, DB_DIR, LOGS_DIR
    global PROV_DB_PATH, BLOCKCHAIN_DB_PATH
    global SAVE_FILE_ORIGINALS_DIR, SAVE_FILE_EMULATED_UPLOADS_DIR
    global MODEL_TRAINING_ARTIFACTS_DIR, MODEL_REGISTRY_PATH, MODEL_TRAINING_PROCESSED_DIR
    global _CUSTOM_DATA_ROOT

    if root is None:
        DATA_DIR = _DEFAULT_DATA_DIR
        SAVE_FILE_ORIGINALS_DIR = _DEFAULT_SAVE_ORIGINALS
        SAVE_FILE_EMULATED_UPLOADS_DIR = _DEFAULT_SAVE_EMULATED
        MODEL_TRAINING_ARTIFACTS_DIR = _DEFAULT_MODEL_TRAINING_ARTIFACTS
        MODEL_TRAINING_PROCESSED_DIR = MODEL_TRAINING_SERVICE_DIR / "data" / "processed"
        _CUSTOM_DATA_ROOT = None
    else:
        DATA_DIR = root.resolve()
        SAVE_FILE_ORIGINALS_DIR = DATA_DIR / "save_file" / "originals"
        SAVE_FILE_EMULATED_UPLOADS_DIR = DATA_DIR / "save_file" / "emulated_uploads"
        MODEL_TRAINING_ARTIFACTS_DIR = DATA_DIR / "model_training" / "artifacts"
        MODEL_TRAINING_PROCESSED_DIR = DATA_DIR / "model_training" / "processed"
        _CUSTOM_DATA_ROOT = DATA_DIR

    MODEL_REGISTRY_PATH = MODEL_TRAINING_ARTIFACTS_DIR / "registry.jsonl"

    RAW_ORIGINALS_DIR = DATA_DIR / "raw_originals"
    NORMALIZED_DIR = DATA_DIR / "normalized"
    ONTOLOGY_DIR = DATA_DIR / "ontology"
    ONTOLOGY_EXPORTS_DIR = DATA_DIR / "ontology_exports"
    EVIDENCE_PACKAGES_DIR = DATA_DIR / "evidence_packages"
    PUBLICATIONS_DIR = DATA_DIR / "publications"
    REPORTS_DIR = DATA_DIR / "reports"
    CYCLES_DIR = DATA_DIR / "cycles"
    PROPERTIES_DIR = DATA_DIR / "properties"
    DB_DIR = DATA_DIR / "db"
    LOGS_DIR = DATA_DIR / "logs"
    PROV_DB_PATH = DB_DIR / "provenance.db"
    BLOCKCHAIN_DB_PATH = DB_DIR / "blockchain_service.db"


def apply_data_root(path: str | Path | None = None, *, reset_runtime: bool = True) -> Path:
    """Define (ou limpa) o data root operacional.

    - ``path`` explícito: usa esse diretório e sincroniza ``AGROTRACE_DATA_ROOT``.
    - ``path is None``: rele a env; se ausente, volta ao default ``frontend/data``.
    """
    if path is not None:
        resolved = Path(path).expanduser().resolve()
        os.environ[_DATA_ROOT_ENV] = str(resolved)
        _apply_resolved_root(resolved)
    else:
        env_root = _resolve_env_data_root()
        if env_root is None and _DATA_ROOT_ENV in os.environ and not os.environ.get(_DATA_ROOT_ENV, "").strip():
            # Env vazia explícita → default
            os.environ.pop(_DATA_ROOT_ENV, None)
        _apply_resolved_root(env_root)

    ensure_data_dirs()

    if reset_runtime:
        try:
            from services import bootstrap as boot

            boot.reset_runtime_state()
            boot.configure_env()
        except Exception:
            # Bootstrap pode ainda não estar importável em imports precoces
            pass

    return DATA_DIR


def ensure_data_dirs() -> None:
    """Cria pastas de dados do protótipo se não existirem."""
    for d in (
        RAW_ORIGINALS_DIR,
        SAVE_FILE_ORIGINALS_DIR,
        SAVE_FILE_EMULATED_UPLOADS_DIR,
        NORMALIZED_DIR,
        ONTOLOGY_DIR,
        ONTOLOGY_EXPORTS_DIR,
        EVIDENCE_PACKAGES_DIR,
        PUBLICATIONS_DIR,
        REPORTS_DIR,
        CYCLES_DIR,
        PROPERTIES_DIR,
        DB_DIR,
        LOGS_DIR,
        MODEL_TRAINING_ARTIFACTS_DIR,
        MODEL_TRAINING_PROCESSED_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


# Inicialização a partir do ambiente (sem reset de runtime — módulo ainda carregando)
_apply_resolved_root(_resolve_env_data_root())

# ── Modos de integração ─────────────────────────────────────────────────────
# USE_MOCK_DATA: força mocks apenas em caminhos de teste explícitos (não no runtime normal).
# USE_DIRECT_FUNCTION_CALLS: integra via chamadas Python diretas (sem HTTP).
# ALLOW_MOCK_FALLBACK: se True, falhas de serviço viram mock silencioso — PROIBIDO no fluxo real.
USE_MOCK_DATA = False
USE_DIRECT_FUNCTION_CALLS = True
ALLOW_MOCK_FALLBACK = False

# ── Identidade visual ───────────────────────────────────────────────────────
# PRESENTATION_MODE: ativa CSS de prints (sem debug menu, sombras suaves, payload claro).
PRESENTATION_MODE = True

APP_TITLE = "AgroTrace Carbon"
APP_SUBTITLE = (
    "Plataforma para gestão, cálculo e acompanhamento de emissões agropecuárias"
)

# ── Layouts de wrapper ──────────────────────────────────────────────────────
LAYOUT_OPTIONS = {
    "intraday": "intraday:v1",
    "monthly": "monthly:v1",
    "annual": "annual:v1",
}

# Status / eventos / etapas: fonte canônica em services.domain_catalog
# (listas duplicadas removidas desta config).

# ── Dash server ─────────────────────────────────────────────────────────────
DASH_HOST = "127.0.0.1"
DASH_PORT = 8050
DEBUG = True

# Blockchain network for anchoring (local_simulated | anvil_local | ethereum_sepolia)
# Prefer BLOCKCHAIN_DEFAULT_NETWORK_CODE env; never default to Sepolia without config.
BLOCKCHAIN_DEFAULT_NETWORK_CODE = os.environ.get(
    "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated"
)

# Logging: AGROTRACE_LOG_LEVEL (default DEBUG), AGROTRACE_LOG_FILE → utils/logging_config.py
