"""Bootstrap de sys.path e bancos SQLite dos serviços."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger("agrotrace.bootstrap")

_BOOTSTRAPPED = False
_PROV_READY = False
_BLOCKCHAIN_READY = False


def _add_to_path(path: Path) -> None:
    s = str(path.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


def _install_wrappers_alias() -> None:
    """Registra meta path finder para importar agrotrace-carbon-wrappers-service como ``wrappers``."""
    import importlib.abc
    import importlib.util

    service_root = config.WRAPPERS_SERVICE_DIR

    class _WrappersAliasFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname != "wrappers" and not fullname.startswith("wrappers."):
                return None
            if fullname == "wrappers":
                init = service_root / "__init__.py"
                return importlib.util.spec_from_file_location(
                    fullname, init, submodule_search_locations=[str(service_root)]
                )
            relative = fullname.removeprefix("wrappers.")
            py_file = service_root / f"{relative.replace('.', '/')}.py"
            if py_file.is_file():
                return importlib.util.spec_from_file_location(fullname, py_file)
            pkg_dir = service_root / relative.replace(".", "/")
            init = pkg_dir / "__init__.py"
            if pkg_dir.is_dir() and init.is_file():
                return importlib.util.spec_from_file_location(
                    fullname, init, submodule_search_locations=[str(pkg_dir)]
                )
            return None

    if not any(getattr(f, "__name__", "") == "_WrappersAliasFinder" for f in sys.meta_path):
        sys.meta_path.insert(0, _WrappersAliasFinder())


def configure_paths() -> None:
    """Adiciona raízes dos serviços ao sys.path."""
    _install_wrappers_alias()
    _add_to_path(config.SAVE_FILE_SERVICE_DIR)
    _add_to_path(config.WRAPPERS_SERVICE_DIR)
    _add_to_path(config.CALCULATION_SERVICE_DIR)
    _add_to_path(config.ONTOLOGY_SERVICE_DIR)
    _add_to_path(config.BLOCKCHAIN_SERVICE_DIR)
    _add_to_path(config.TRACEABILITY_SRC_DIR)
    # Necessário para unpickle de forecasters (model.joblib de séries temporais).
    _add_to_path(config.MODEL_TRAINING_SERVICE_DIR / "src")


def configure_env() -> None:
    """Define variáveis de ambiente das DBs."""
    config.ensure_data_dirs()
    prov_url = f"sqlite:///{config.PROV_DB_PATH.as_posix()}"
    os.environ["PROV_DATABASE_URL"] = prov_url
    os.environ["BLOCKCHAIN_DATABASE_URL"] = f"sqlite:///{config.BLOCKCHAIN_DB_PATH.as_posix()}"
    os.environ["BLOCKCHAIN_PROVENANCE_DATABASE_URL"] = str(config.PROV_DB_PATH)


def reset_runtime_state() -> None:
    """Limpa flags/caches para permitir trocar o data root sem reiniciar o processo."""
    global _BOOTSTRAPPED, _PROV_READY, _BLOCKCHAIN_READY
    _BOOTSTRAPPED = False
    _PROV_READY = False
    _BLOCKCHAIN_READY = False

    try:
        from provenance_service.infrastructure.config import get_settings
        from provenance_service.infrastructure.db import clear_engine_cache

        clear_engine_cache()
        get_settings.cache_clear()
    except Exception:
        pass

    try:
        from app.shared.config import get_settings as get_chain_settings

        get_chain_settings.cache_clear()
    except Exception:
        pass

    try:
        import services.provenance_adapter as provenance_adapter

        provenance_adapter._recorder = None
        provenance_adapter._uow_factory = None
        provenance_adapter._reviewer_agent_id = None
    except Exception:
        pass

    try:
        import services.save_file_adapter as save_file_adapter

        save_file_adapter._service_cache = None
    except Exception:
        pass

    try:
        from utils.file_helpers import invalidate_cycle_cache

        invalidate_cycle_cache()
    except Exception:
        pass

    try:
        import utils.logging_config as logging_config

        logging_config.reset_logging_for_data_root()
    except Exception:
        pass


def init_provenance_db() -> bool:
    """Inicializa DB de proveniência (idempotente)."""
    global _PROV_READY
    if _PROV_READY:
        return True
    try:
        from provenance_service.infrastructure.config import get_settings
        from provenance_service.infrastructure.db import Base, clear_engine_cache
        from provenance_service.infrastructure.db.models import (  # noqa: F401
            audit,
            calculation,
            pipeline,
            prov_core,
            reporting,
            semantic,
        )
        from provenance_service.infrastructure.db.session import create_engine_from_settings
        from provenance_service.infrastructure.db.sqlite_append_only import (
            install_sqlite_append_only,
        )

        clear_engine_cache()
        get_settings.cache_clear()
        engine = create_engine_from_settings()
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            install_sqlite_append_only(conn)
        engine.dispose()
        _PROV_READY = True
        logger.info("Provenance DB inicializada: %s", config.PROV_DB_PATH)
        return True
    except Exception as exc:
        logger.warning("Falha ao inicializar provenance DB: %s", exc)
        return False


def init_blockchain_db() -> tuple[Any | None, bool]:
    """Inicializa DB blockchain e retorna ServiceContainer."""
    global _BLOCKCHAIN_READY
    if _BLOCKCHAIN_READY:
        try:
            from app.application.container import ServiceContainer
            from app.shared.config import Settings, get_settings

            get_settings.cache_clear()
            settings = Settings(
                database_url=f"sqlite:///{config.BLOCKCHAIN_DB_PATH.as_posix()}",
                provenance_database_url=str(config.PROV_DB_PATH),
            )
            return ServiceContainer(settings), True
        except Exception:
            return None, False

    try:
        from app.application.container import ServiceContainer, init_database
        from app.shared.config import Settings, get_settings

        get_settings.cache_clear()
        settings = Settings(
            database_url=f"sqlite:///{config.BLOCKCHAIN_DB_PATH.as_posix()}",
            provenance_database_url=str(config.PROV_DB_PATH),
        )
        container = ServiceContainer(settings)
        init_database(container.settings)
        _BLOCKCHAIN_READY = True
        logger.info("Blockchain DB inicializada: %s", config.BLOCKCHAIN_DB_PATH)
        return container, True
    except Exception as exc:
        logger.warning("Falha ao inicializar blockchain DB: %s", exc)
        return None, False


def _wipe_directory(directory: Path) -> int:
    """Remove arquivos de um diretório (preserva .gitkeep). Retorna quantidade removida."""
    removed = 0
    if not directory.exists():
        return removed
    for path in directory.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            path.unlink(missing_ok=True)
            removed += 1
        elif path.is_dir():
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed


def wipe_all_test_data(*, recreate_dbs: bool = True) -> dict[str, Any]:
    """Apaga todos os artefatos locais de teste do protótipo."""
    config.ensure_data_dirs()
    reset_runtime_state()

    wiped: dict[str, int] = {}
    for directory in (
        config.CYCLES_DIR,
        config.RAW_ORIGINALS_DIR,
        config.SAVE_FILE_ORIGINALS_DIR,
        config.SAVE_FILE_EMULATED_UPLOADS_DIR,
        config.NORMALIZED_DIR,
        config.ONTOLOGY_DIR,
        config.ONTOLOGY_EXPORTS_DIR,
        config.EVIDENCE_PACKAGES_DIR,
        config.PUBLICATIONS_DIR,
        config.REPORTS_DIR,
    ):
        wiped[str(directory.name)] = _wipe_directory(directory)

    wiped["properties"] = _wipe_directory(config.PROPERTIES_DIR)

    for db_path in (config.PROV_DB_PATH, config.BLOCKCHAIN_DB_PATH):
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError as exc:
                raise PermissionError(
                    f"Não foi possível apagar {db_path}. Feche o frontend (python main.py) e tente novamente."
                ) from exc

    if recreate_dbs:
        boot = bootstrap_all()
        return {"wiped": wiped, "bootstrap": boot}
    return {"wiped": wiped, "bootstrap": None}


def reset_local_data() -> dict[str, bool]:
    """Apaga dados locais do protótipo e recria bancos SQLite."""
    result = wipe_all_test_data(recreate_dbs=True)
    return result.get("bootstrap") or {}


def bootstrap_all() -> dict[str, bool]:
    """Executa bootstrap completo uma vez."""
    global _BOOTSTRAPPED
    configure_paths()
    configure_env()

    prov_ok = init_provenance_db()
    container, chain_ok = init_blockchain_db()

    _BOOTSTRAPPED = True
    return {
        "paths": True,
        "provenance_db": prov_ok,
        "blockchain_db": chain_ok,
        "container": container is not None,
    }


def get_blockchain_container() -> Any | None:
    """Retorna container blockchain já inicializado."""
    container, ok = init_blockchain_db()
    return container if ok else None
