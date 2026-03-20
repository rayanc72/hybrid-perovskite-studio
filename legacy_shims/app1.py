"""Compatibility shim for the packaged Streamlit app entrypoint."""

from __future__ import annotations

import sys
import importlib
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    module_name = "hpame.ui.app_main"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


if __name__ == "__main__":
    main()
