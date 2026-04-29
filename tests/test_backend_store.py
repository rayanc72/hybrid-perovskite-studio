from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.services.backend_store import BackendStore


class BackendStoreTests(unittest.TestCase):
    def test_job_lifecycle_and_artifact_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(
                db_path=root / "jobs.sqlite3",
                artifact_dir=root / "artifacts",
            )

            job_id = store.create_job(
                workflow="structure_summary",
                request_hash="abc123",
                payload={"file_name": "demo.cif"},
            )
            store.update_job(job_id, state="running", progress=0.5, append_message="Half way there.")
            artifact_id = store.create_artifact(
                kind="structure_summary",
                data=json.dumps({"atom_count": 42}).encode("utf-8"),
                content_type="application/json",
                suffix=".json",
            )
            store.update_job(job_id, state="completed", progress=1.0, result_ref=artifact_id)

            job = store.get_job(job_id)
            self.assertIsNotNone(job)
            self.assertEqual(job["state"], "completed")
            self.assertEqual(job["result_ref"], artifact_id)
            self.assertIn("Half way there.", job["messages"])

            artifact = store.get_artifact(artifact_id)
            self.assertIsNotNone(artifact)
            self.assertEqual(artifact["content_type"], "application/json")
            self.assertTrue(Path(artifact["path"]).exists())

    def test_completed_job_cache_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(
                db_path=root / "jobs.sqlite3",
                artifact_dir=root / "artifacts",
            )

            job_id = store.create_job(
                workflow="structure_summary",
                request_hash="hash-1",
                payload={"file_name": "demo.cif"},
            )
            store.update_job(job_id, state="completed", progress=1.0)

            cached_job = store.find_completed_job(workflow="structure_summary", request_hash="hash-1")
            self.assertIsNotNone(cached_job)
            self.assertEqual(cached_job["job_id"], job_id)


if __name__ == "__main__":
    unittest.main()
