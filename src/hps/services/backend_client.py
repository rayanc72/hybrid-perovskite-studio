"""Small stdlib HTTP client used by the Streamlit UI to talk to the local backend."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hps.services.backend_runtime import backend_base_url, backend_is_healthy, ensure_local_backend_running


class BackendClientError(RuntimeError):
    """Raised when the local backend cannot be reached or returns an invalid response."""


LEGACY_WORKFLOW_ALIASES = {
    "structure_context": "structure_summary",
}


def ensure_backend_ready() -> str:
    if backend_is_healthy():
        return backend_base_url()
    return ensure_local_backend_running()


def _request_json(method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    url = f"{ensure_backend_ready().rstrip('/')}{path}"
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise BackendClientError(f"Backend request failed: {exc.code} {message}") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise BackendClientError(f"Backend request failed: {exc}") from exc


def submit_job(workflow: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        return _request_json("POST", f"/jobs/{workflow}", payload)
    except BackendClientError as exc:
        fallback_workflow = LEGACY_WORKFLOW_ALIASES.get(workflow)
        if fallback_workflow and "404" in str(exc) and "Unknown workflow" in str(exc):
            return _request_json("POST", f"/jobs/{fallback_workflow}", payload)
        raise


def get_job(job_id: str) -> dict[str, object]:
    return _request_json("GET", f"/jobs/{job_id}")


def cancel_job(job_id: str) -> dict[str, object]:
    return _request_json("POST", f"/jobs/{job_id}/cancel")


def get_artifact(artifact_id: str) -> dict[str, object]:
    return _request_json("GET", f"/artifacts/{artifact_id}")
