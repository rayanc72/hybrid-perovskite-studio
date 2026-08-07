from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.io.paths import (
    APP_BACKEND_ARTIFACTS_DIR,
    APP_BACKEND_DIR,
    APP_CACHE_DIR,
    APP_OUTPUT_DIR,
    APP_TMP_DIR,
    REPO_ROOT,
    SRC_ROOT,
    ensure_runtime_dirs,
)
from hps.services.backend_runtime import backend_base_url, validate_backend_connection


class RuntimeHelperTests(unittest.TestCase):
    def test_repo_paths_are_consistent(self) -> None:
        self.assertEqual(REPO_ROOT, ROOT)
        self.assertEqual(SRC_ROOT, ROOT / "src")

    def test_runtime_dirs_can_be_created(self) -> None:
        ensure_runtime_dirs()
        self.assertTrue(APP_OUTPUT_DIR.exists())
        self.assertTrue(APP_TMP_DIR.exists())
        self.assertTrue(APP_CACHE_DIR.exists())
        self.assertTrue(APP_BACKEND_DIR.exists())
        self.assertTrue(APP_BACKEND_ARTIFACTS_DIR.exists())

    def test_backend_startup_validation_reports_service_identity(self) -> None:
        health = {"status": "ok", "service": "hps-backend", "version": "1.2.3"}
        with (
            patch(
                "hps.services.backend_runtime.ensure_local_backend_running",
                return_value="http://127.0.0.1:8765",
            ),
            patch("hps.services.backend_runtime.backend_health", return_value=health),
        ):
            result = validate_backend_connection()

        self.assertEqual(result["base_url"], "http://127.0.0.1:8765")
        self.assertEqual(result["version"], "1.2.3")

    def test_backend_base_url_respects_local_host_and_port(self) -> None:
        with patch.dict(
            "os.environ",
            {"HPS_BACKEND_HOST": "127.0.0.2", "HPS_BACKEND_PORT": "9876"},
            clear=True,
        ):
            self.assertEqual(backend_base_url(), "http://127.0.0.2:9876")

    def test_backend_startup_validation_rejects_unversioned_service(self) -> None:
        health = {"status": "ok", "service": "hps-backend"}
        with (
            patch(
                "hps.services.backend_runtime.ensure_local_backend_running",
                return_value="http://127.0.0.1:8765",
            ),
            patch("hps.services.backend_runtime.backend_health", return_value=health),
        ):
            with self.assertRaisesRegex(RuntimeError, "did not report"):
                validate_backend_connection()


if __name__ == "__main__":
    unittest.main()
