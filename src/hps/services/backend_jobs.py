"""Workflow registry and background job manager for the local API service."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from concurrent.futures import Future, ProcessPoolExecutor
from threading import Lock

from hps.core.electronic import parse_pdos_payload
from hps.core.md import parse_md_outputs
from hps.core.structure import summarize_structure_upload
from hps.core.structure import calculate_space_group_sweep, simulate_pxrd_from_upload
from hps.services.backend_store import BackendStore


class UnknownWorkflowError(ValueError):
    """Raised when a caller requests an unknown backend workflow."""


def _run_structure_summary(payload: dict[str, object]) -> dict[str, object]:
    file_bytes = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    return summarize_structure_upload(
        file_name=str(payload["file_name"]),
        file_bytes=file_bytes,
        exceptions=payload.get("exceptions"),
        bond_padding=float(payload.get("bond_padding", 0.0)),
    )


def _run_structure_context(payload: dict[str, object]) -> dict[str, object]:
    return _run_structure_summary(payload)


def _run_structure_symmetry(payload: dict[str, object]) -> dict[str, object]:
    file_bytes = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    return calculate_space_group_sweep(
        file_name=str(payload["file_name"]),
        file_bytes=file_bytes,
        symprec_lower=float(payload["symprec_lower"]),
        symprec_upper=float(payload["symprec_upper"]),
        angle_tol=float(payload["angle_tol"]),
    )


def _run_structure_pxrd(payload: dict[str, object]) -> dict[str, object]:
    file_bytes = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    return simulate_pxrd_from_upload(
        file_name=str(payload["file_name"]),
        file_bytes=file_bytes,
        wavelength=float(payload.get("wavelength", 1.5406)),
        two_theta_range=tuple(payload.get("two_theta_range", (5.0, 80.0))),
        fwhm=float(payload.get("fwhm", 0.1)),
        x_axis=str(payload.get("x_axis", "2theta")),
        scaled=bool(payload.get("scaled", True)),
        num_points=int(payload.get("num_points", 4000)),
    )


def _decode_named_files(payload_files: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized_files = []
    for file in payload_files:
        normalized_files.append(
            {
                "name": str(file["name"]),
                "content": base64.b64decode(str(file["content_b64"]).encode("utf-8")),
            }
        )
    return normalized_files


def _run_electronic_pdos(payload: dict[str, object]) -> dict[str, object]:
    files = _decode_named_files(list(payload.get("files", [])))
    return parse_pdos_payload(
        files,
        combination_text=str(payload.get("combination_text", "")),
    )


def _run_md_parse(payload: dict[str, object]) -> dict[str, object]:
    files = _decode_named_files(list(payload.get("files", [])))
    return parse_md_outputs(files)


WORKFLOW_REGISTRY = {
    "structure_summary": _run_structure_summary,
    "structure_context": _run_structure_context,
    "structure_symmetry": _run_structure_symmetry,
    "structure_pxrd": _run_structure_pxrd,
    "electronic_pdos": _run_electronic_pdos,
    "md_parse": _run_md_parse,
}


def execute_workflow(workflow: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        handler = WORKFLOW_REGISTRY[workflow]
    except KeyError as exc:
        raise UnknownWorkflowError(f"Unknown workflow: {workflow}") from exc
    return handler(payload)


class BackendJobManager:
    """Queue local jobs, persist state, and reuse cached completed results."""

    def __init__(self, store: BackendStore | None = None, *, max_workers: int | None = None) -> None:
        self.store = store or BackendStore()
        self._executor = ProcessPoolExecutor(max_workers=max_workers or max(1, min(2, os.cpu_count() or 1)))
        self._futures: dict[str, Future] = {}
        self._lock = Lock()

    def compute_request_hash(self, workflow: str, payload: dict[str, object]) -> str:
        normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256()
        digest.update(workflow.encode("utf-8"))
        digest.update(b":")
        digest.update(normalized_payload.encode("utf-8"))
        return digest.hexdigest()

    def submit(self, workflow: str, payload: dict[str, object]) -> dict[str, object]:
        request_hash = self.compute_request_hash(workflow, payload)
        cached_job = self.store.find_completed_job(workflow=workflow, request_hash=request_hash)
        if cached_job is not None:
            return cached_job

        job_id = self.store.create_job(workflow=workflow, request_hash=request_hash, payload=payload)
        self.store.update_job(
            job_id,
            state="running",
            progress=0.1,
            append_message="Job accepted by the local backend.",
        )

        future = self._executor.submit(execute_workflow, workflow, payload)
        with self._lock:
            self._futures[job_id] = future
        future.add_done_callback(lambda done_future, current_job_id=job_id, current_workflow=workflow: self._finalize_job(current_job_id, current_workflow, done_future))
        return self.store.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, object] | None:
        return self.store.get_job(job_id)

    def cancel(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            future = self._futures.get(job_id)
        if future is None:
            return self.store.get_job(job_id)

        cancelled = future.cancel()
        if cancelled:
            self.store.update_job(
                job_id,
                state="cancelled",
                progress=1.0,
                append_message="Job cancelled before execution started.",
            )
        else:
            self.store.update_job(
                job_id,
                append_message="Cancellation requested, but the job is already running.",
            )
        return self.store.get_job(job_id)

    def _finalize_job(self, job_id: str, workflow: str, future: Future) -> None:
        try:
            result = future.result()
            artifact_id = self.store.create_artifact(
                kind=workflow,
                data=json.dumps(result, indent=2, sort_keys=True).encode("utf-8"),
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
        except Exception as exc:
            self.store.update_job(
                job_id,
                state="failed",
                progress=1.0,
                error=str(exc),
                append_message="Job failed during backend execution.",
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)


_JOB_MANAGER: BackendJobManager | None = None


def get_job_manager() -> BackendJobManager:
    global _JOB_MANAGER
    if _JOB_MANAGER is None:
        _JOB_MANAGER = BackendJobManager()
    return _JOB_MANAGER
