"""FastAPI app exposing local background workflows for the Streamlit UI."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from hps import __version__
from hps.api.schemas import (
    ElectronicBandRequest,
    ElectronicPdosRequest,
    ElectronicSpinRequest,
    HealthResponse,
    JobStatusResponse,
    MdParseRequest,
    MdTrajectoryRequest,
    StructurePdfRequest,
    StructurePdfCompareRequest,
    StructureRdfRequest,
    StructurePxrdRequest,
    StructureSummaryRequest,
    StructureSymmetryRequest,
)
from hps.services.backend_jobs import UnknownWorkflowError, get_job_manager

app = FastAPI(title="Hybrid Perovskite Studio Backend", version=__version__)

WORKFLOW_SCHEMAS = {
    "structure_summary": StructureSummaryRequest,
    "structure_context": StructureSummaryRequest,
    "structure_symmetry": StructureSymmetryRequest,
    "structure_pxrd": StructurePxrdRequest,
    "structure_pdf": StructurePdfRequest,
    "structure_pdf_compare": StructurePdfCompareRequest,
    "structure_rdf": StructureRdfRequest,
    "electronic_pdos": ElectronicPdosRequest,
    "electronic_band": ElectronicBandRequest,
    "electronic_spin": ElectronicSpinRequest,
    "md_parse": MdParseRequest,
    "md_trajectory_prepare": MdTrajectoryRequest,
}


def _serialize_job(job: dict[str, object] | None) -> JobStatusResponse:
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(
        job_id=str(job["job_id"]),
        workflow=str(job["workflow"]),
        state=str(job["state"]),
        progress=float(job["progress"]),
        messages=list(job["messages"]),
        result_ref=job["result_ref"],
        error=job["error"],
        cache_hit=bool(job.get("cache_hit", False)),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="hps-backend")


@app.post("/jobs/{workflow}", response_model=JobStatusResponse)
def submit_job(workflow: str, payload: dict[str, object]) -> JobStatusResponse:
    try:
        schema = WORKFLOW_SCHEMAS.get(workflow)
        if schema is None:
            raise UnknownWorkflowError(f"Unknown workflow: {workflow}")
        validated_payload = schema.model_validate(payload).model_dump()
        job = get_job_manager().submit(workflow, validated_payload)
        return _serialize_job(job)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    return _serialize_job(get_job_manager().get_job(job_id))


@app.post("/jobs/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_job(job_id: str) -> JobStatusResponse:
    return _serialize_job(get_job_manager().cancel(job_id))


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    artifact = get_job_manager().store.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    content_type = str(artifact["content_type"])
    path = str(artifact["path"])
    if content_type == "application/json":
        with open(path, "r", encoding="utf-8") as handle:
            return JSONResponse(content=json.load(handle))
    return FileResponse(path, media_type=content_type)
