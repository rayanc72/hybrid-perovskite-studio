"""Allow ``python -m hps`` to launch the app."""

from __future__ import annotations

from hps.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
