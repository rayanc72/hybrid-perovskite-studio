"""Helpers for loading the legacy top-level application and modules."""

from __future__ import annotations

import importlib
import runpy
import sys

from hpame.io.paths import LEGACY_ENTRYPOINT, LEGACY_SHIMS_DIR, REPO_ROOT, ensure_runtime_dirs


def ensure_repo_root_on_path() -> None:
    """Allow package code to import the legacy top-level modules."""
    for path in (str(REPO_ROOT), str(LEGACY_SHIMS_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)


def import_legacy_module(module_name: str):
    """Import a legacy module on demand."""
    ensure_repo_root_on_path()
    return importlib.import_module(module_name)


def run_legacy_app() -> None:
    """Execute the legacy Streamlit entrypoint in-process."""
    ensure_runtime_dirs()
    ensure_repo_root_on_path()
    runpy.run_path(str(LEGACY_ENTRYPOINT), run_name="__main__")
