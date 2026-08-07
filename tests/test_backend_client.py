from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.services.backend_client import BackendClientError, submit_job


class BackendClientTests(unittest.TestCase):
    def test_submit_job_retries_legacy_structure_context_alias(self) -> None:
        payload = {"file_name": "demo.cif", "file_bytes_b64": "Zm9v"}
        responses = [
            BackendClientError('Backend request failed: 404 {"detail":"Unknown workflow: structure_context"}'),
            {"job_id": "job-123", "workflow": "structure_summary", "state": "queued"},
        ]

        with patch("hps.services.backend_client._request_json", side_effect=responses) as request_json:
            job = submit_job("structure_context", payload)

        self.assertEqual(job["job_id"], "job-123")
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(request_json.call_args_list[0].args, ("POST", "/jobs/structure_context", payload))
        self.assertEqual(request_json.call_args_list[1].args, ("POST", "/jobs/structure_summary", payload))

    def test_submit_job_does_not_retry_non_alias_workflow(self) -> None:
        payload = {"value": 1}

        with patch(
            "hps.services.backend_client._request_json",
            side_effect=BackendClientError('Backend request failed: 404 {"detail":"Unknown workflow: other"}'),
        ) as request_json:
            with self.assertRaises(BackendClientError):
                submit_job("other", payload)

        self.assertEqual(request_json.call_count, 1)


if __name__ == "__main__":
    unittest.main()
