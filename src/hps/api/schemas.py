"""Pydantic schemas for the local HPS backend."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StructureSummaryRequest(BaseModel):
    file_name: str
    file_bytes_b64: str
    exceptions: list[tuple[str, str]] = Field(default_factory=list)
    bond_padding: float = 0.0


class StructureSymmetryRequest(BaseModel):
    file_name: str
    file_bytes_b64: str
    symprec_lower: float
    symprec_upper: float
    angle_tol: float


class StructurePxrdRequest(BaseModel):
    file_name: str
    file_bytes_b64: str
    wavelength: float = 1.5406
    two_theta_range: tuple[float, float] = (5.0, 80.0)
    fwhm: float = 0.1
    x_axis: str = "2theta"
    scaled: bool = True
    num_points: int = 4000


class NamedContentFile(BaseModel):
    name: str
    content_b64: str


class ElectronicPdosRequest(BaseModel):
    files: list[NamedContentFile] = Field(default_factory=list)
    combination_text: str = ""


class MdParseRequest(BaseModel):
    files: list[NamedContentFile] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    workflow: str
    state: str
    progress: float
    messages: list[str]
    result_ref: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
