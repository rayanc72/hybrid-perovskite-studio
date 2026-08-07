"""Streamlit-independent state handling for local backend workflows."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from collections.abc import Callable, MutableMapping, Sequence
from typing import Any

from hps.services.backend_client import BackendClientError, get_artifact, get_job, submit_job

WorkflowState = dict[str, Any]


def normalize_payload(value: Any) -> Any:
    """Return a deterministic JSON-compatible representation of a request payload."""

    if isinstance(value, dict):
        return {
            str(key): normalize_payload(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [normalize_payload(item) for item in value]
    return value


def workflow_signature(workflow: str, payload: dict[str, object]) -> str:
    digest = hashlib.sha256()
    digest.update(workflow.encode("utf-8"))
    digest.update(b":")
    digest.update(
        json.dumps(normalize_payload(payload), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    return digest.hexdigest()


def named_file_payload(uploaded_files: Sequence[Any] | None) -> list[dict[str, str]]:
    """Serialize Streamlit-style uploaded files for a backend request."""

    return [
        {
            "name": uploaded_file.name,
            "content_b64": base64.b64encode(uploaded_file.getvalue()).decode("utf-8"),
        }
        for uploaded_file in uploaded_files or []
    ]


def empty_workflow_state(signature: str) -> WorkflowState:
    return {
        "signature": signature,
        "job_id": None,
        "status": None,
        "result": None,
        "error": None,
        "messages": [],
    }


def get_workflow_state(
    registry: MutableMapping[str, WorkflowState], state_key: str
) -> WorkflowState:
    return registry.get(state_key, {})


def run_workflow(
    registry: MutableMapping[str, WorkflowState],
    workflow: str,
    payload: dict[str, object],
    state_key: str,
    *,
    start: bool = False,
    poll_timeout: float = 6.0,
    submit: Callable[[str, dict[str, object]], dict[str, object]] = submit_job,
    fetch_job: Callable[[str], dict[str, object]] = get_job,
    fetch_artifact: Callable[[str], object] = get_artifact,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> object | None:
    """Submit or poll a workflow while maintaining a serializable UI state record."""

    signature = workflow_signature(workflow, payload)
    state = registry.get(state_key, empty_workflow_state(signature))
    if state.get("signature") != signature:
        state = empty_workflow_state(signature)

    if state.get("result") is not None:
        registry[state_key] = state
        return state["result"]

    if state.get("job_id") is None and start:
        try:
            submitted_job = submit(workflow, payload)
        except BackendClientError as exc:
            state["status"] = "failed"
            state["error"] = str(exc)
            registry[state_key] = state
            return None
        state["job_id"] = submitted_job["job_id"]
        _update_state_from_job(state, submitted_job)
        if submitted_job["state"] == "completed" and submitted_job.get("result_ref"):
            _load_result(state, str(submitted_job["result_ref"]), fetch_artifact)
            registry[state_key] = state
            return state.get("result")

    if state.get("job_id") is None:
        registry[state_key] = state
        return None

    deadline = monotonic() + max(0.0, poll_timeout)
    while monotonic() < deadline:
        try:
            job = fetch_job(str(state["job_id"]))
        except BackendClientError as exc:
            state["status"] = "failed"
            state["error"] = str(exc)
            break

        _update_state_from_job(state, job)
        if job["state"] == "completed" and job.get("result_ref"):
            _load_result(state, str(job["result_ref"]), fetch_artifact)
            break
        if job["state"] in {"failed", "cancelled"}:
            break
        sleep(0.1)

    registry[state_key] = state
    return state.get("result")


def _update_state_from_job(state: WorkflowState, job: dict[str, object]) -> None:
    state["status"] = job["state"]
    state["messages"] = job.get("messages", [])
    state["error"] = job.get("error")


def _load_result(
    state: WorkflowState,
    result_ref: str,
    fetch_artifact: Callable[[str], object],
) -> None:
    try:
        state["result"] = fetch_artifact(result_ref)
    except BackendClientError as exc:
        state["status"] = "failed"
        state["error"] = str(exc)
