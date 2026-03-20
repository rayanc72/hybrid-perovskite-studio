"""Compatibility layer around the legacy flat-file app."""

from .loader import ensure_repo_root_on_path, import_legacy_module, run_legacy_app

__all__ = ["ensure_repo_root_on_path", "import_legacy_module", "run_legacy_app"]
