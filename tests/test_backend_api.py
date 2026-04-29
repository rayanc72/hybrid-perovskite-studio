from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from fastapi.testclient import TestClient

    import hps.services.backend_jobs as backend_jobs_module
    from hps.api.app import app
    from hps.services.backend_store import BackendStore
except Exception as exc:  # pragma: no cover - environment dependent
    TestClient = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


TEST_CIF = """data_test
_symmetry_space_group_name_H-M 'P 1'
_cell_length_a    4.0
_cell_length_b    4.0
_cell_length_c    4.0
_cell_angle_alpha 90
_cell_angle_beta  90
_cell_angle_gamma 90
loop_
  _atom_site_label
  _atom_site_type_symbol
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  Na1 Na 0.0 0.0 0.0
  Cl1 Cl 0.5 0.5 0.5
"""


@unittest.skipIf(TestClient is None, f"Optional test dependency unavailable: {_IMPORT_ERROR}")
class BackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        self._previous_manager = backend_jobs_module._JOB_MANAGER
        store = BackendStore(
            db_path=root / "jobs.sqlite3",
            artifact_dir=root / "artifacts",
        )
        backend_jobs_module._JOB_MANAGER = _ImmediateJobManager(store)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        backend_jobs_module._JOB_MANAGER = self._previous_manager
        self._tmpdir.cleanup()

    def _await_job(self, job_id: str, timeout: float = 5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = self.client.get(f"/jobs/{job_id}")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            if payload["state"] in {"completed", "failed", "cancelled"}:
                return payload
            time.sleep(0.1)
        self.fail(f"Job {job_id} did not finish before timeout.")

    def test_structure_pxrd_job_and_artifact(self) -> None:
        response = self.client.post(
            "/jobs/structure_pxrd",
            json={
                "file_name": "demo.cif",
                "file_bytes_b64": base64.b64encode(TEST_CIF.encode("utf-8")).decode("utf-8"),
                "wavelength": 1.5406,
                "two_theta_range": [5.0, 40.0],
                "fwhm": 0.1,
                "x_axis": "2theta",
                "scaled": True,
                "num_points": 200,
            },
        )
        self.assertEqual(response.status_code, 200)
        job = self._await_job(response.json()["job_id"])
        self.assertEqual(job["state"], "completed")
        artifact = self.client.get(f"/artifacts/{job['result_ref']}")
        self.assertEqual(artifact.status_code, 200)
        payload = artifact.json()
        self.assertIn("profile", payload)
        self.assertIn("reflections", payload)

    def test_electronic_pdos_job_and_cache_hit(self) -> None:
        total = base64.b64encode(b"-2 1\n0 2\n2 1\n").decode("utf-8")
        pb = base64.b64encode(b"-2 0 1 2\n0 0 2 3\n2 0 1 1\n").decode("utf-8")
        iodine = base64.b64encode(b"-2 4\n0 5\n2 4\n").decode("utf-8")
        payload = {
            "files": [
                {"name": "KS_DOS_total.dat", "content_b64": total},
                {"name": "Pb_l_proj_dos.dat", "content_b64": pb},
                {"name": "I_l_proj_dos.dat", "content_b64": iodine},
            ],
            "combination_text": "PbI = Pb(s) + Pb(p) + I",
        }

        response_one = self.client.post("/jobs/electronic_pdos", json=payload)
        self.assertEqual(response_one.status_code, 200)
        job_one = self._await_job(response_one.json()["job_id"])
        self.assertEqual(job_one["state"], "completed")

        response_two = self.client.post("/jobs/electronic_pdos", json=payload)
        self.assertEqual(response_two.status_code, 200)
        job_two = response_two.json()
        self.assertEqual(job_two["state"], "completed")
        self.assertEqual(job_one["job_id"], job_two["job_id"])

    def test_md_parse_invalid_payload_is_rejected(self) -> None:
        response = self.client.post("/jobs/md_parse", json={"files": [{"name": "broken.out"}]})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()


class _ImmediateJobManager:
    def __init__(self, store: BackendStore) -> None:
        self.store = store

    def submit(self, workflow: str, payload: dict[str, object]) -> dict[str, object]:
        request_hash = self.compute_request_hash(workflow, payload)
        cached_job = self.store.find_completed_job(workflow=workflow, request_hash=request_hash)
        if cached_job is not None:
            return cached_job

        job_id = self.store.create_job(workflow=workflow, request_hash=request_hash, payload=payload)
        self.store.update_job(job_id, state="running", progress=0.1, append_message="Job accepted by the local backend.")
        try:
            result = backend_jobs_module.execute_workflow(workflow, payload)
            artifact_id = self.store.create_artifact(
                kind=workflow,
                data=backend_jobs_module.json.dumps(result, indent=2, sort_keys=True).encode("utf-8"),
                content_type="application/json",
                suffix=".json",
            )
            self.store.update_job(
                job_id,
                state="completed",
                progress=1.0,
                result_ref=artifact_id,
                append_message="Job finished successfully.",
            )
        except Exception as exc:  # pragma: no cover - defensive
            self.store.update_job(
                job_id,
                state="failed",
                progress=1.0,
                error=str(exc),
                append_message="Job failed during backend execution.",
            )
        return self.store.get_job(job_id)

    def get_job(self, job_id: str):
        return self.store.get_job(job_id)

    def cancel(self, job_id: str):
        return self.store.get_job(job_id)

    @staticmethod
    def compute_request_hash(workflow: str, payload: dict[str, object]) -> str:
        digest = hashlib.sha256()
        digest.update(workflow.encode("utf-8"))
        digest.update(b":")
        digest.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return digest.hexdigest()
