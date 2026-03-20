"""Compatibility shim for the packaged PDF analysis module."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from hpame.domain.pdf_analysis import *  # noqa: F401,F403
