from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hpame.io.paths import (
    APP_OUTPUT_DIR,
    APP_TMP_DIR,
    REPO_ROOT,
    SRC_ROOT,
    ensure_runtime_dirs,
)


class RuntimeHelperTests(unittest.TestCase):
    def test_repo_paths_are_consistent(self) -> None:
        self.assertEqual(REPO_ROOT, ROOT)
        self.assertEqual(SRC_ROOT, ROOT / "src")

    def test_runtime_dirs_can_be_created(self) -> None:
        ensure_runtime_dirs()
        self.assertTrue(APP_OUTPUT_DIR.exists())
        self.assertTrue(APP_TMP_DIR.exists())


if __name__ == "__main__":
    unittest.main()
