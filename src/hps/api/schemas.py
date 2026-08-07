"""Pydantic schemas for the local HPS backend."""

from __future__ import annotations

import base64
import binascii
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_UPLOAD_BASE64_CHARS = ((MAX_UPLOAD_BYTES + 2) // 3) * 4
MAX_BATCH_FILES = 100


def _validate_base64_upload(value: str) -> str:
    if len(value) > MAX_UPLOAD_BASE64_CHARS:
        raise ValueError(f"Encoded upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Upload content must be valid base64.") from exc
    if len(decoded) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Decoded upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.")
    return value


class StructureSummaryRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    exceptions: list[tuple[str, str]] = Field(default_factory=list, max_length=100)
    bond_padding: float = Field(default=0.0, ge=0.0, le=5.0)

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)


class StructureSymmetryRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    symprec_lower: float = Field(gt=0.0, le=10.0)
    symprec_upper: float = Field(gt=0.0, le=10.0)
    angle_tol: float = Field(ge=0.0, le=180.0)

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)

    @model_validator(mode="after")
    def validate_symmetry_range(self):
        if self.symprec_lower > self.symprec_upper:
            raise ValueError("symprec_lower must not exceed symprec_upper.")
        return self


class StructurePxrdRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    wavelength: float = Field(default=1.5406, gt=0.0, le=100.0)
    two_theta_range: tuple[float, float] = (5.0, 80.0)
    fwhm: float = Field(default=0.1, ge=0.0, le=20.0)
    x_axis: Literal["2theta", "q"] = "2theta"
    scaled: bool = True
    num_points: int = Field(default=4000, ge=10, le=100_000)

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)

    @model_validator(mode="after")
    def validate_two_theta_range(self):
        lower, upper = self.two_theta_range
        if lower < 0.0 or upper > 180.0 or lower >= upper:
            raise ValueError("two_theta_range must be increasing and within 0 to 180 degrees.")
        return self


class StructurePdfRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    q_range: tuple[float, float] = (1.0, 20.0)
    r_range: tuple[float, float] = (0.1, 20.0)
    qdamp: float = Field(default=0.06, ge=0.0, le=10.0)
    qbroad: float = Field(default=0.06, ge=0.0, le=10.0)

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.q_range[0] < 0 or self.q_range[0] >= self.q_range[1]:
            raise ValueError("q_range must be increasing and non-negative.")
        if self.r_range[0] < 0 or self.r_range[0] >= self.r_range[1]:
            raise ValueError("r_range must be increasing and non-negative.")
        return self


class StructurePdfCompareRequest(BaseModel):
    simulated_r: list[float] = Field(min_length=2, max_length=200_000)
    simulated_g: list[float] = Field(min_length=2, max_length=200_000)
    experimental_r: list[float] = Field(min_length=2, max_length=200_000)
    experimental_g: list[float] = Field(min_length=2, max_length=200_000)
    normalization: Literal["zscore", "minmax"] = "zscore"

    @model_validator(mode="after")
    def validate_lengths(self):
        if len(self.simulated_r) != len(self.simulated_g):
            raise ValueError("simulated_r and simulated_g lengths must match.")
        if len(self.experimental_r) != len(self.experimental_g):
            raise ValueError("experimental_r and experimental_g lengths must match.")
        return self


class StructureRdfRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    atom_list: list[str] = Field(min_length=1, max_length=20)
    r_max: float = Field(gt=0.0, le=1_000.0)
    bins: int = Field(ge=10, le=100_000)
    weighted: bool = True

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)


class NamedContentFile(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)

    _valid_upload = field_validator("content_b64")(_validate_base64_upload)


class ElectronicPdosRequest(BaseModel):
    files: list[NamedContentFile] = Field(default_factory=list, max_length=MAX_BATCH_FILES)
    combination_text: str = Field(default="", max_length=10_000)

    @model_validator(mode="after")
    def validate_total_upload_size(self):
        if sum(len(file.content_b64) for file in self.files) > MAX_UPLOAD_BASE64_CHARS:
            raise ValueError("Combined uploads exceed the request size limit.")
        return self


class ElectronicBandRequest(BaseModel):
    files: list[NamedContentFile] = Field(min_length=1, max_length=MAX_BATCH_FILES)
    energy_shift: float = Field(default=0.0, ge=-1_000.0, le=1_000.0)

    @model_validator(mode="after")
    def validate_total_upload_size(self):
        if sum(len(file.content_b64) for file in self.files) > MAX_UPLOAD_BASE64_CHARS:
            raise ValueError("Combined uploads exceed the request size limit.")
        return self


class ElectronicSpinRequest(BaseModel):
    files: list[NamedContentFile] = Field(min_length=1, max_length=MAX_BATCH_FILES)

    @model_validator(mode="after")
    def validate_total_upload_size(self):
        if sum(len(file.content_b64) for file in self.files) > MAX_UPLOAD_BASE64_CHARS:
            raise ValueError("Combined uploads exceed the request size limit.")
        return self


class MdParseRequest(BaseModel):
    files: list[NamedContentFile] = Field(default_factory=list, max_length=MAX_BATCH_FILES)

    @model_validator(mode="after")
    def validate_total_upload_size(self):
        if sum(len(file.content_b64) for file in self.files) > MAX_UPLOAD_BASE64_CHARS:
            raise ValueError("Combined uploads exceed the request size limit.")
        return self


class MdTrajectoryRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_bytes_b64: str = Field(min_length=1, max_length=MAX_UPLOAD_BASE64_CHARS)
    timestep_fs: float = Field(gt=0.0, le=1_000_000.0)

    _valid_upload = field_validator("file_bytes_b64")(_validate_base64_upload)


class JobStatusResponse(BaseModel):
    job_id: str
    workflow: str
    state: str
    progress: float
    messages: list[str]
    result_ref: str | None = None
    error: str | None = None
    cache_hit: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
