"""Primary packaged Streamlit entrypoint."""

from __future__ import annotations

import os
import sys
import importlib
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hps.services.runtime import legacy_app_is_runnable
from hps.services.backend_runtime import ensure_local_backend_running
from hps.ui import render_bootstrap_page


def _patch_streamlit_watcher() -> None:
    """Skip problematic pseudo-modules during Streamlit source watching."""
    try:
        from streamlit.watcher import local_sources_watcher as lsw
    except Exception:
        return

    original_get_module_paths = lsw.get_module_paths

    def safe_get_module_paths(module):
        module_name = getattr(module, "__name__", "")
        if module_name.startswith("torch.classes"):
            return set()
        try:
            return original_get_module_paths(module)
        except Exception:
            return set()

    lsw.get_module_paths = safe_get_module_paths


def main() -> None:
    os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
    _patch_streamlit_watcher()
    try:
        ensure_local_backend_running()
    except Exception:
        # The UI can still render without the backend and surface a softer warning.
        pass
    if legacy_app_is_runnable():
        module_name = "hps.ui.app_main"
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)
        return
    render_bootstrap_page()


if __name__ == "__main__":
    main()
