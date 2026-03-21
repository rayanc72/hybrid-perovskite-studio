"""Console entrypoints for Hybrid Perovskite Studio."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Launch the packaged Streamlit app via ``hps``."""
    from streamlit.web.cli import main as streamlit_main

    app_path = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app_path)]
    return streamlit_main()


if __name__ == "__main__":
    raise SystemExit(main())
