# Hybrid Perovskite Studio Architecture

## Current layout

The repository now runs from a package-centered layout under `src/hps/`.

- `src/hps/app.py` is the supported entrypoint
- `src/hps/domain/` provides narrow, lazy wrappers around the current scientific modules instead of importing them eagerly at package import time
- `src/hps/services/runtime.py` owns dependency-group checks and bootstrap behavior
- `src/hps/services/backend_runtime.py` owns local backend discovery and startup
- `src/hps/services/backend_jobs.py` and `src/hps/services/backend_store.py` manage background jobs, caching, and artifact persistence
- `src/hps/io/paths.py` defines shared runtime locations for `output/` and `tmp/`
- `src/hps/api/` exposes the local FastAPI backend
- `src/hps/core/` holds Streamlit-free workflow helpers extracted from the monolith

- `src/hps/ui/app_main.py` contains the packaged app implementation copied from the legacy entrypoint
- `src/hps/ui/navigation.py` is the single source of truth for workspace names, workspace descriptions, and the feature-map tree
- `src/hps/domain/pdf_analysis.py` contains the packaged PDF analysis implementation copied from the legacy module

## Current backend-migrated workflows

The local backend/job layer is now used for the highest-value parsing and preprocessing paths that were repeatedly re-running inside Streamlit:

- structure context / upload summary
- structure symmetry sweeps
- PXRD simulation
- PDOS parsing and table preparation
- MD output parsing

These workflows currently flow through:

- `src/hps/ui/app_main.py` for UI submission and result rendering
- `src/hps/services/backend_client.py` for local API calls
- `src/hps/api/app.py` for HTTP endpoints
- `src/hps/services/backend_jobs.py` for workflow registration and caching
- `src/hps/core/` for Streamlit-free execution helpers

The remaining expensive workflows, especially PDF analysis and zipped trajectory analysis, still need to move over incrementally.

## Boundaries

### UI layer

Files under `src/hps/ui/` should contain Streamlit rendering logic, labels, and user-facing messaging.

The UI should prefer backend job submission for expensive workflows and should avoid parsing or recomputing heavy state during unrelated reruns.

Navigation-specific guidance:

- [src/hps/ui/navigation.py](../src/hps/ui/navigation.py) should be updated when workspace structure changes
- [src/hps/ui/app_main.py](../src/hps/ui/app_main.py) should consume that registry rather than redefining the same tree by hand

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
