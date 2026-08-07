"""Workflow registry and background job manager for the local API service."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from concurrent.futures import Executor, Future, ProcessPoolExecutor
from threading import Lock

import pandas as pd

from hps.core.electronic import (
    parse_band_payload,
    parse_pdos_payload,
    parse_spin_texture_payload,
)
from hps.core.md import parse_md_outputs, prepare_trajectory_exports
from hps.core.structure import (
    calculate_space_group_sweep,
    compare_pdf_profiles,
    simulate_pdf_from_upload,
    simulate_pxrd_from_upload,
    simulate_rdf_from_upload,
    summarize_structure_upload,
)
from hps.services.backend_store import BackendStore


class UnknownWorkflowError(ValueError):
    """Raised when a caller requests an unknown backend workflow."""


INTERNAL_ARTIFACTS_KEY = "_hps_artifacts"
CACHE_SCHEMA_VERSION = "2"


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


def _run_structure_pdf(payload: dict[str, object]) -> dict[str, object]:
    file_bytes = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    return simulate_pdf_from_upload(
        file_name=str(payload["file_name"]),
        file_bytes=file_bytes,
        q_range=tuple(payload.get("q_range", (1.0, 20.0))),
        r_range=tuple(payload.get("r_range", (0.1, 20.0))),
        qdamp=float(payload.get("qdamp", 0.06)),
        qbroad=float(payload.get("qbroad", 0.06)),
    )


def _run_structure_pdf_compare(payload: dict[str, object]) -> dict[str, object]:
    return compare_pdf_profiles(
        simulated_r=list(payload["simulated_r"]),
        simulated_g=list(payload["simulated_g"]),
        experimental_r=list(payload["experimental_r"]),
        experimental_g=list(payload["experimental_g"]),
        normalization=str(payload.get("normalization", "zscore")),
    )


def _run_structure_rdf(payload: dict[str, object]) -> dict[str, object]:
    file_bytes = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    return simulate_rdf_from_upload(
        file_name=str(payload["file_name"]),
        file_bytes=file_bytes,
        atom_list=[str(value) for value in payload["atom_list"]],
        r_max=float(payload["r_max"]),
        bins=int(payload["bins"]),
        weighted=bool(payload.get("weighted", True)),
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


def _run_electronic_band(payload: dict[str, object]) -> dict[str, object]:
    return parse_band_payload(
        _decode_named_files(list(payload.get("files", []))),
        energy_shift=float(payload.get("energy_shift", 0.0)),
    )


def _run_electronic_spin(payload: dict[str, object]) -> dict[str, object]:
    return parse_spin_texture_payload(_decode_named_files(list(payload.get("files", []))))


def _run_md_parse(payload: dict[str, object]) -> dict[str, object]:
    files = _decode_named_files(list(payload.get("files", [])))
    result = parse_md_outputs(files)
    result[INTERNAL_ARTIFACTS_KEY] = [
        {
            "name": "data_csv",
            "file_name": "md_output.csv",
            "content_type": "text/csv",
            "suffix": ".csv",
            "data": pd.DataFrame(result["table"], columns=result["columns"])
            .to_csv(index=False)
            .encode("utf-8"),
        }
    ]
    return result


def _run_md_trajectory_prepare(payload: dict[str, object]) -> dict[str, object]:
    content = base64.b64decode(str(payload["file_bytes_b64"]).encode("utf-8"))
    result, exports = prepare_trajectory_exports(content, float(payload["timestep_fs"]))
    result[INTERNAL_ARTIFACTS_KEY] = exports
    return result


WORKFLOW_REGISTRY = {
    "structure_summary": _run_structure_summary,
    "structure_context": _run_structure_context,
    "structure_symmetry": _run_structure_symmetry,
    "structure_pxrd": _run_structure_pxrd,
    "structure_pdf": _run_structure_pdf,
    "structure_pdf_compare": _run_structure_pdf_compare,
    "structure_rdf": _run_structure_rdf,
    "electronic_pdos": _run_electronic_pdos,
    "electronic_band": _run_electronic_band,
    "electronic_spin": _run_electronic_spin,
    "md_parse": _run_md_parse,
    "md_trajectory_prepare": _run_md_trajectory_prepare,
}

ARTIFACT_TYPES = {
    workflow: {"content_type": "application/json", "suffix": ".json"}
    for workflow in WORKFLOW_REGISTRY
}


def execute_workflow(workflow: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        handler = WORKFLOW_REGISTRY[workflow]
    except KeyError as exc:
        raise UnknownWorkflowError(f"Unknown workflow: {workflow}") from exc
    return handler(payload)


def execute_workflow_profiled(
    workflow: str, payload: dict[str, object]
) -> tuple[dict[str, object], float]:
    """Execute a workflow and return its result with process-local elapsed time."""

    started_at = time.perf_counter()
    result = execute_workflow(workflow, payload)
    duration_ms = max(0.0, (time.perf_counter() - started_at) * 1000.0)
    return result, duration_ms


def persist_workflow_result(store: BackendStore, workflow: str, result: dict[str, object]) -> str:
    """Persist a workflow's downloads and compact JSON result as backend artifacts."""

    persisted_result = dict(result)
    artifact_payloads = list(persisted_result.pop(INTERNAL_ARTIFACTS_KEY, []))
    exports: dict[str, dict[str, object]] = {}
    for artifact_payload in artifact_payloads:
        name = str(artifact_payload["name"])
        data = artifact_payload["data"]
        if not isinstance(data, bytes):
            raise TypeError(f"Workflow export {name!r} must contain bytes.")
        content_type = str(artifact_payload.get("content_type", "application/octet-stream"))
        artifact_id = store.create_artifact(
            kind=f"{workflow}:{name}",
            data=data,
            content_type=content_type,
            suffix=str(artifact_payload.get("suffix", ".bin")),
        )
        exports[name] = {
            "artifact_id": artifact_id,
            "file_name": str(artifact_payload.get("file_name", name)),
            "content_type": content_type,
            "size_bytes": len(data),
        }
    if exports:
        persisted_result["exports"] = exports

    artifact_type = ARTIFACT_TYPES[workflow]
    return store.create_artifact(
        kind=workflow,
        data=json.dumps(persisted_result, indent=2, sort_keys=True).encode("utf-8"),
        content_type=artifact_type["content_type"],
        suffix=artifact_type["suffix"],
    )


class BackendJobManager:
    """Queue local jobs, persist state, and reuse cached completed results."""

    def __init__(
        self,
        store: BackendStore | None = None,
        *,
        max_workers: int | None = None,
        executor: Executor | None = None,
    ) -> None:
        self.store = store or BackendStore()
        self.store.recover_stale_jobs(
            stale_after_seconds=int(os.getenv("HPS_STALE_JOB_SECONDS", "3600"))
        )
        self.store.prune_artifacts(
            max_age_days=int(os.getenv("HPS_ARTIFACT_MAX_AGE_DAYS", "30")),
            max_total_bytes=int(os.getenv("HPS_ARTIFACT_MAX_BYTES", "2000000000")),
            keep_at_least=int(os.getenv("HPS_ARTIFACT_KEEP_AT_LEAST", "20")),
        )
        self._executor = executor or ProcessPoolExecutor(
            max_workers=max_workers or max(1, min(2, os.cpu_count() or 1))
        )
        self._futures: dict[str, Future] = {}
        self._lock = Lock()

    def compute_request_hash(self, workflow: str, payload: dict[str, object]) -> str:
        normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256()
        digest.update(CACHE_SCHEMA_VERSION.encode("utf-8"))
        digest.update(b":")
        digest.update(workflow.encode("utf-8"))
        digest.update(b":")
        digest.update(normalized_payload.encode("utf-8"))
        return digest.hexdigest()

    def submit(self, workflow: str, payload: dict[str, object]) -> dict[str, object]:
        request_hash = self.compute_request_hash(workflow, payload)
        cached_job = self.store.find_completed_job(workflow=workflow, request_hash=request_hash)
        if cached_job is not None:
            return cached_job

        job_id = self.store.create_job(
            workflow=workflow, request_hash=request_hash, payload=payload
        )
        self.store.update_job(
            job_id,
            state="running",
            progress=0.1,
            append_message="Job accepted by the local backend.",
        )

        future = self._executor.submit(execute_workflow_profiled, workflow, payload)
        with self._lock:
            self._futures[job_id] = future
        future.add_done_callback(
            lambda done_future, current_job_id=job_id, current_workflow=workflow: (
                self._finalize_job(current_job_id, current_workflow, done_future)
            )
        )
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
            result, execution_duration_ms = future.result()
            artifact_id = persist_workflow_result(self.store, workflow, result)
            self.store.update_job(
                job_id,
                state="completed",
                progress=1.0,
                result_ref=artifact_id,
                execution_duration_ms=execution_duration_ms,
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
