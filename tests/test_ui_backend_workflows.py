from __future__ import annotations

import base64
import io
import unittest

from hps.services.backend_client import BackendClientError
from hps.ui.backend_workflows import named_file_payload, run_workflow, workflow_signature


class UploadedBytes(io.BytesIO):
    def __init__(self, name: str, content: bytes) -> None:
        super().__init__(content)
        self.name = name


class BackendWorkflowUiTests(unittest.TestCase):
    def test_signature_is_stable_across_mapping_order(self) -> None:
        first = workflow_signature("demo", {"b": 2, "a": {"y": 1, "x": 0}})
        second = workflow_signature("demo", {"a": {"x": 0, "y": 1}, "b": 2})
        self.assertEqual(first, second)

    def test_named_file_payload_encodes_bytes(self) -> None:
        payload = named_file_payload([UploadedBytes("input.dat", b"content")])
        self.assertEqual(payload[0]["name"], "input.dat")
        self.assertEqual(base64.b64decode(payload[0]["content_b64"]), b"content")

    def test_completed_submission_loads_and_caches_artifact(self) -> None:
        registry = {}
        submit_calls = []

        def submit(workflow, payload):
            submit_calls.append((workflow, payload))
            return {
                "job_id": "job-1",
                "state": "completed",
                "result_ref": "artifact-1",
                "messages": ["done"],
                "error": None,
            }

        first = run_workflow(
            registry,
            "demo",
            {"value": 1},
            "state",
            start=True,
            submit=submit,
            fetch_artifact=lambda artifact_id: {"artifact": artifact_id},
        )
        second = run_workflow(
            registry,
            "demo",
            {"value": 1},
            "state",
            start=True,
            submit=submit,
        )

        self.assertEqual(first, {"artifact": "artifact-1"})
        self.assertEqual(second, first)
        self.assertEqual(len(submit_calls), 1)

    def test_submission_failure_is_stored(self) -> None:
        registry = {}

        def fail(_workflow, _payload):
            raise BackendClientError("backend unavailable")

        result = run_workflow(
            registry,
            "demo",
            {},
            "state",
            start=True,
            submit=fail,
        )
        self.assertIsNone(result)
        self.assertEqual(registry["state"]["status"], "failed")
        self.assertIn("backend unavailable", registry["state"]["error"])
