"""Shared repository paths for the packaged app."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SRC_ROOT.parent
APP_OUTPUT_DIR = REPO_ROOT / "output"
APP_TMP_DIR = REPO_ROOT / "tmp"
LEGACY_SHIMS_DIR = REPO_ROOT / "legacy_shims"
LEGACY_ENTRYPOINT = LEGACY_SHIMS_DIR / "app1.py"


def ensure_runtime_dirs() -> None:
    """Create conventional runtime directories if they do not already exist."""
    APP_OUTPUT_DIR.mkdir(exist_ok=True)
    APP_TMP_DIR.mkdir(exist_ok=True)
