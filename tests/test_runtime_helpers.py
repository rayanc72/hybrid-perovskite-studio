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
    LEGACY_ENTRYPOINT,
    LEGACY_SHIMS_DIR,
    REPO_ROOT,
    SRC_ROOT,
    ensure_runtime_dirs,
)
from hpame.legacy.loader import ensure_repo_root_on_path


class RuntimeHelperTests(unittest.TestCase):
    def test_repo_paths_are_consistent(self) -> None:
        self.assertEqual(REPO_ROOT, ROOT)
        self.assertEqual(SRC_ROOT, ROOT / "src")
        self.assertEqual(LEGACY_SHIMS_DIR, ROOT / "legacy_shims")
        self.assertEqual(LEGACY_ENTRYPOINT, ROOT / "legacy_shims" / "app1.py")

    def test_runtime_dirs_can_be_created(self) -> None:
        ensure_runtime_dirs()
        self.assertTrue(APP_OUTPUT_DIR.exists())
        self.assertTrue(APP_TMP_DIR.exists())

    def test_repo_root_can_be_added_to_sys_path(self) -> None:
        ensure_repo_root_on_path()
        self.assertIn(str(ROOT), sys.path)


if __name__ == "__main__":
    unittest.main()
