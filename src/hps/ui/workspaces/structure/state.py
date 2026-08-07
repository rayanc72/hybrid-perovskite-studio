"""State and backend-summary lifecycle for the Structure workspace."""

from __future__ import annotations

import base64
import hashlib
import io
from collections.abc import Callable, MutableMapping
from typing import Any

from hps.services.backend_client import BackendClientError, get_artifact, get_job, submit_job

STRUCTURE_STATE_DEFAULTS = {
    "file_name": None,
    "uploaded_structure_name": None,
    "uploaded_structure_bytes": None,
    "structure_uploader_key": 0,
    "structure_summary_signature": None,
    "structure_summary_job_id": None,
    "structure_summary_data": None,
    "structure_summary_status": None,
    "structure_summary_error": None,
    "show_structure_details": False,
    "load_initial_structure_viewer": False,
}


def initialize_state(state: MutableMapping[str, Any]) -> None:
    for key, default in STRUCTURE_STATE_DEFAULTS.items():
        if key not in state:
            state[key] = default


def structure_upload_signature(file_name: str, file_bytes: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(file_name.encode("utf-8"))
    digest.update(b":")
    digest.update(file_bytes)
    return digest.hexdigest()


def reset_summary(state: MutableMapping[str, Any]) -> None:
    state["structure_summary_signature"] = None
    state["structure_summary_job_id"] = None
    state["structure_summary_data"] = None
    state["structure_summary_status"] = None
    state["structure_summary_error"] = None


def clear_loaded_structure(state: MutableMapping[str, Any]) -> None:
    initialize_state(state)
    state["uploaded_structure_name"] = None
    state["uploaded_structure_bytes"] = None
    state["file_name"] = None
    state["structure_uploader_key"] += 1
    state["show_structure_details"] = False
    state["load_initial_structure_viewer"] = False
    reset_summary(state)


def store_upload(
    state: MutableMapping[str, Any],
    file_name: str,
    file_bytes: bytes,
) -> None:
    initialize_state(state)
    state["uploaded_structure_name"] = file_name
    state["uploaded_structure_bytes"] = file_bytes
    state["file_name"] = file_name


def prime_summary_job(
    state: MutableMapping[str, Any],
    uploaded_name: str,
    uploaded_bytes: bytes,
    *,
    submit: Callable[[str, dict[str, object]], dict[str, object]] = submit_job,
) -> None:
    initialize_state(state)
    signature = structure_upload_signature(uploaded_name, uploaded_bytes)
    if state["structure_summary_signature"] == signature:
        return

    reset_summary(state)
    state["structure_summary_signature"] = signature
    payload = {
        "file_name": uploaded_name,
        "file_bytes_b64": base64.b64encode(uploaded_bytes).decode("utf-8"),
        "exceptions": [["F", "I"]],
        "bond_padding": 0.0,
    }

    try:
        job = submit("structure_summary", payload)
    except BackendClientError as exc:
        state["structure_summary_error"] = str(exc)
        state["structure_summary_status"] = "failed"
        return

    state["structure_summary_job_id"] = job["job_id"]
    state["structure_summary_status"] = job["state"]


def refresh_summary_status(
    state: MutableMapping[str, Any],
    *,
    fetch_job: Callable[[str], dict[str, object]] = get_job,
    fetch_artifact: Callable[[str], object] = get_artifact,
) -> None:
    job_id = state.get("structure_summary_job_id")
    if not job_id or state.get("structure_summary_data") is not None:
        return

    try:
        job = fetch_job(str(job_id))
    except BackendClientError as exc:
        state["structure_summary_error"] = str(exc)
        state["structure_summary_status"] = "failed"
        return

    state["structure_summary_status"] = job["state"]
    if job["state"] == "completed" and job.get("result_ref"):
        try:
            state["structure_summary_data"] = fetch_artifact(str(job["result_ref"]))
        except BackendClientError as exc:
            state["structure_summary_error"] = str(exc)
            state["structure_summary_status"] = "failed"
    elif job["state"] == "failed":
        state["structure_summary_error"] = (
            job.get("error") or "Background structure summary failed."
        )


def load_active_structure(state: MutableMapping[str, Any]):
    """Parse the active upload into the legacy atoms/molecules tuple."""

    from hps.domain.structure_manager import get_file_format, initialize_structure

    uploaded_name = state.get("uploaded_structure_name")
    uploaded_bytes = state.get("uploaded_structure_bytes")
    if not uploaded_name or uploaded_bytes is None:
        return None

    structure_buffer = io.BytesIO(uploaded_bytes)
    structure_buffer.name = uploaded_name
    return initialize_structure(
        structure_buffer,
        file_format=get_file_format(uploaded_name),
        file_name=uploaded_name,
        exceptions=[("F", "I")],
        b_p=0,
    )
