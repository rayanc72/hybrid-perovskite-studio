from __future__ import annotations

import base64
import unittest

from hps.services.backend_client import BackendClientError
from hps.ui.workspaces.structure.state import (
    clear_loaded_structure,
    initialize_state,
    prime_summary_job,
    refresh_summary_status,
    store_upload,
)


class StructureWorkspaceStateTests(unittest.TestCase):
    def test_initialization_and_clear_reset_all_structure_state(self) -> None:
        state = {}
        initialize_state(state)
        store_upload(state, "demo.cif", b"content")
        state["structure_summary_data"] = {"atom_count": 1}

        clear_loaded_structure(state)

        self.assertIsNone(state["uploaded_structure_name"])
        self.assertIsNone(state["uploaded_structure_bytes"])
        self.assertIsNone(state["structure_summary_data"])
        self.assertEqual(state["structure_uploader_key"], 1)

    def test_summary_submission_is_deduplicated_by_content_signature(self) -> None:
        state = {}
        initialize_state(state)
        submissions = []

        def submit(workflow, payload):
            submissions.append((workflow, payload))
            return {"job_id": "job-1", "state": "queued"}

        prime_summary_job(state, "demo.cif", b"content", submit=submit)
        prime_summary_job(state, "demo.cif", b"content", submit=submit)

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0][0], "structure_summary")
        self.assertEqual(base64.b64decode(submissions[0][1]["file_bytes_b64"]), b"content")

    def test_completed_summary_loads_artifact(self) -> None:
        state = {}
        initialize_state(state)
        state["structure_summary_job_id"] = "job-1"

        refresh_summary_status(
            state,
            fetch_job=lambda _job_id: {
                "state": "completed",
                "result_ref": "artifact-1",
            },
            fetch_artifact=lambda artifact_id: {"artifact": artifact_id},
        )

        self.assertEqual(state["structure_summary_status"], "completed")
        self.assertEqual(state["structure_summary_data"], {"artifact": "artifact-1"})

    def test_backend_failure_is_exposed_in_state(self) -> None:
        state = {}
        initialize_state(state)

        def fail(_workflow, _payload):
            raise BackendClientError("offline")

        prime_summary_job(state, "demo.cif", b"content", submit=fail)
        self.assertEqual(state["structure_summary_status"], "failed")
        self.assertIn("offline", state["structure_summary_error"])
