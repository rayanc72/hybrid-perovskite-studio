"""Shared repository paths for the packaged app."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SRC_ROOT.parent
APP_OUTPUT_DIR = REPO_ROOT / "output"
APP_TMP_DIR = REPO_ROOT / "tmp"
APP_CACHE_DIR = APP_TMP_DIR / "cache"
APP_BACKEND_DIR = APP_TMP_DIR / "backend"
APP_BACKEND_DB = APP_BACKEND_DIR / "jobs.sqlite3"
APP_BACKEND_ARTIFACTS_DIR = APP_BACKEND_DIR / "artifacts"
APP_BACKEND_LOG = APP_BACKEND_DIR / "backend.log"


def ensure_runtime_dirs() -> None:
    """Create conventional runtime directories if they do not already exist."""
    APP_OUTPUT_DIR.mkdir(exist_ok=True)
    APP_TMP_DIR.mkdir(exist_ok=True)
    APP_CACHE_DIR.mkdir(exist_ok=True)
    APP_BACKEND_DIR.mkdir(exist_ok=True)
    APP_BACKEND_ARTIFACTS_DIR.mkdir(exist_ok=True)
