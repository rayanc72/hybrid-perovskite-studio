"""Shared repository paths for the packaged app."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SRC_ROOT.parent
APP_OUTPUT_DIR = REPO_ROOT / "output"
APP_TMP_DIR = REPO_ROOT / "tmp"


def ensure_runtime_dirs() -> None:
    """Create conventional runtime directories if they do not already exist."""
    APP_OUTPUT_DIR.mkdir(exist_ok=True)
    APP_TMP_DIR.mkdir(exist_ok=True)
