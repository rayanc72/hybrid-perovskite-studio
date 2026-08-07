# Hybrid Perovskite Studio Architecture

## Current layout

The repository now runs from a package-centered layout under `src/hps/`.

- `src/hps/app.py` is the supported entrypoint
- `src/hps/domain/` provides narrow, lazy wrappers around the current scientific modules instead of importing them eagerly at package import time
- `src/hps/services/runtime.py` owns dependency-group checks and bootstrap behavior
- `src/hps/services/backend_runtime.py` owns local backend discovery and startup
- `src/hps/services/backend_jobs.py` and `src/hps/services/backend_store.py` manage background jobs, caching, and artifact persistence
- `src/hps/ui/backend_workflows.py` owns Streamlit-independent workflow signatures, polling state, and uploaded-file request serialization
- `src/hps/ui/workspaces/structure/state.py` owns active-upload state and structure-summary job lifecycle
- `src/hps/ui/workspaces/structure/overview.py` renders structure upload, metadata, downloads, details, and the opt-in 3D viewer
- `src/hps/ui/workspaces/structure/navigation.py` maps the shared feature registry to a typed Structure selection
- `src/hps/ui/workspaces/structure/analysis/` contains focused symmetry, PXRD, PDF, structure-metric, and charge-parser modules
- `src/hps/ui/workspaces/structure/transformations/rotation.py` owns the rotation workflow family
- `src/hps/ui/workspaces/structure/transformations/operations.py` owns reflection, translation, deletion, labelling, and interpolation rendering
- `src/hps/ui/workspaces/electronic.py`, `dynamics.py`, and `utilities.py` own their workspace renderers
- `src/hps/io/paths.py` defines shared runtime locations for `output/` and `tmp/`
- `src/hps/api/` exposes the local FastAPI backend
- `src/hps/core/` holds Streamlit-free workflow helpers extracted from the monolith

- `src/hps/ui/app_main.py` is the workspace coordinator and delegates feature rendering to `src/hps/ui/workspaces/`
- `src/hps/ui/navigation.py` is the single source of truth for workspace names, workspace descriptions, and the feature-map tree
- `src/hps/domain/pdf_analysis.py` contains the packaged PDF analysis implementation copied from the legacy module

## Current backend-migrated workflows

The local backend/job layer is now used for the highest-value parsing and preprocessing paths that were repeatedly re-running inside Streamlit:

- structure context / upload summary
- structure symmetry sweeps
- PXRD simulation
- PDF simulation
- PDOS parsing and table preparation
- bandstructure and spin-texture preprocessing
- MD output parsing
- trajectory archive validation and inventory

These workflows currently flow through:

- `src/hps/ui/workspaces/structure/analysis/` for Structure symmetry, PXRD, and PDF submission and result rendering
- focused modules under `src/hps/ui/workspaces/` for UI submission and result rendering
- `src/hps/services/backend_client.py` for local API calls
- `src/hps/api/app.py` for HTTP endpoints
- `src/hps/services/backend_jobs.py` for workflow registration and caching
- `src/hps/core/` for Streamlit-free execution helpers

Artifact retention, cache-hit accounting, and stale-job recovery are handled by the backend store and configured through the `HPS_ARTIFACT_*` and `HPS_STALE_JOB_SECONDS` environment variables.

## Boundaries

### UI layer

Files under `src/hps/ui/` should contain Streamlit rendering logic, labels, and user-facing messaging.

The packaged UI now imports its scientific dependencies explicitly. Dynamic namespace injection is prohibited so missing names are caught by static analysis before a workflow is opened.

The UI should prefer backend job submission for expensive workflows and should avoid parsing or recomputing heavy state during unrelated reruns.

Navigation-specific guidance:

- [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py) should be updated when workspace structure changes
- [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py) should consume that registry rather than redefining the same tree by hand

### Service layer

Files under `src/hps/services/` should coordinate app behavior, environment checks, and cross-module orchestration.

The local backend job system belongs here rather than in the Streamlit layer.

### Domain layer

Files under `src/hps/domain/` should expose scientific operations through narrow interfaces. They should not contain app bootstrap or dependency-install logic.

As mixed modules are refactored, Streamlit-free computational helpers should move into `src/hps/core/` when they are intended for backend execution.

### IO layer

Files under `src/hps/io/` should handle repository paths, output conventions, and file/runtime helpers.

## Dependency policy

- `pyproject.toml` is the source of truth for installation metadata
- `requirements.txt` is a compatibility wrapper that installs the editable package with `full` and `dev` extras
- Optional dependency groups are separated by concern: `core`, `md`, `pdf`, `viz`, `auth`
- Backend API dependencies live in the `backend` extra
- The current UI requires the `full` stack because of the scientific dependencies used across the packaged modules

## Guardrails

- No wildcard imports in `src/hps/`
- New package modules should prefer lazy imports when scientific imports are optional or heavy
- Runtime artifacts should go under `output/` or `tmp/`
- New work should target the package tree first
