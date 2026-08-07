from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.services.backend_jobs import persist_workflow_result
from hps.services.backend_store import BackendStore


class BackendStoreTests(unittest.TestCase):
    def test_workflow_exports_are_persisted_separately_from_json_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(root / "jobs.sqlite3", root / "artifacts")
            result_ref = persist_workflow_result(
                store,
                "md_parse",
                {
                    "row_count": 1,
                    "_hps_artifacts": [
                        {
                            "name": "data_csv",
                            "file_name": "md_output.csv",
                            "content_type": "text/csv",
                            "suffix": ".csv",
                            "data": b"Time [ps]\n0.0\n",
                        }
                    ],
                },
            )

            result_path = Path(store.get_artifact(result_ref)["path"])
            persisted = json.loads(result_path.read_text())
            export = persisted["exports"]["data_csv"]
            self.assertNotIn("_hps_artifacts", persisted)
            self.assertEqual(export["file_name"], "md_output.csv")
            export_path = Path(store.get_artifact(export["artifact_id"])["path"])
            self.assertEqual(export_path.read_bytes(), b"Time [ps]\n0.0\n")

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
            store.update_job(
                job_id,
                state="completed",
                progress=1.0,
                result_ref=artifact_id,
                execution_duration_ms=12.5,
            )

            job = store.get_job(job_id)
            self.assertIsNotNone(job)
            self.assertEqual(job["state"], "completed")
            self.assertEqual(job["result_ref"], artifact_id)
            self.assertEqual(job["execution_duration_ms"], 12.5)
            self.assertIn("Half way there.", job["messages"])

            artifact = store.get_artifact(artifact_id)
            self.assertIsNotNone(artifact)
            self.assertEqual(artifact["content_type"], "application/json")
            self.assertTrue(Path(artifact["path"]).exists())

    def test_uploaded_content_is_not_duplicated_in_job_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(root / "jobs.sqlite3", root / "artifacts")
            job_id = store.create_job(
                workflow="md_trajectory_prepare",
                request_hash="archive-hash",
                payload={"file_name": "trajectory.zip", "file_bytes_b64": "YWJj"},
            )

            payload = store.get_job(job_id)["payload"]
            stored_upload = payload["file_bytes_b64"]
            self.assertTrue(stored_upload["redacted"])
            self.assertEqual(stored_upload["encoded_size"], 4)
            self.assertNotIn("YWJj", json.dumps(payload))

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
            self.assertTrue(cached_job["cache_hit"])
            self.assertEqual(cached_job["cache_hit_count"], 1)

    def test_stale_jobs_are_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(root / "jobs.sqlite3", root / "artifacts")
            job_id = store.create_job(
                workflow="structure_summary", request_hash="stale", payload={}
            )
            store.update_job(job_id, state="running")
            with sqlite3.connect(root / "jobs.sqlite3") as conn:
                conn.execute(
                    "UPDATE jobs SET updated_at = datetime('now', '-2 hours') WHERE job_id = ?",
                    (job_id,),
                )
            assert store.recover_stale_jobs(stale_after_seconds=60) == 1
            assert store.get_job(job_id)["state"] == "failed"

    def test_artifact_retention_expires_cached_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = BackendStore(root / "jobs.sqlite3", root / "artifacts")
            job_id = store.create_job(
                workflow="electronic_band", request_hash="old", payload={}
            )
            artifact_id = store.create_artifact(kind="electronic_band", data=b"result")
            store.update_job(job_id, state="completed", progress=1.0, result_ref=artifact_id)
            result = store.prune_artifacts(
                max_age_days=0, max_total_bytes=0, keep_at_least=0
            )
            assert result["deleted_count"] == 1
            assert store.get_artifact(artifact_id) is None
            assert store.get_job(job_id)["state"] == "expired"


if __name__ == "__main__":
    unittest.main()
