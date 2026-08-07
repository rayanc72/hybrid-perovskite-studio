# Backend Modernization

This page tracks the current state of the Streamlit-to-backend migration and the intended direction for the next development phases.

## What Has Already Landed

HPS now has a local backend service and job/cache layer built around:

- `FastAPI` endpoints in `src/hps/api/`
- a local job manager in `src/hps/services/backend_jobs.py`
- SQLite-backed job and artifact persistence in `src/hps/services/backend_store.py`
- Streamlit-free backend helpers in `src/hps/core/`

The Streamlit app auto-starts the local backend when possible and uses it for a growing subset of expensive workflows.

## Workflows Already Using The Backend

The following workflows are now submitted through the backend instead of being parsed entirely inside the Streamlit rerun loop:

- `structure_context`
  - used for structure upload summary and cached structure metadata
- `structure_symmetry`
  - used for space-group sweep generation in the Structure workspace
- `structure_pxrd`
  - used for PXRD profile and reflection-table generation
- `structure_pdf`
  - used for optional PDF simulation before PDF/RDF plotting and comparison
- `electronic_pdos`
  - used for PDOS file-role detection, parsing, table generation, and combination preparation
- `electronic_band` and `electronic_spin`
  - used for reusable band-segment and spin-texture preprocessing
- `md_parse`
  - used for parsing AIMS MD output files into tabular timeseries data
- `md_trajectory_prepare`
  - used for safe archive validation, frame inventory, and duration metadata

## Why This Matters

These migrations reduce repeated parsing work inside `src/hps/ui/app_main.py` and make it possible to:

- reuse cached results for repeated inputs
- move long-running work off the most fragile rerun paths
- expose stable backend contracts for future UI refactors
- profile execution in a more controlled service layer

## Artifact Lifecycle

Backend startup recovers abandoned queued/running jobs and prunes derived artifacts according to:

- `HPS_STALE_JOB_SECONDS` (default `3600`)
- `HPS_ARTIFACT_MAX_AGE_DAYS` (default `30`)
- `HPS_ARTIFACT_MAX_BYTES` (default `2000000000`)
- `HPS_ARTIFACT_KEEP_AT_LEAST` (default `20`)

Completed-job cache hits are recorded, missing artifacts are never returned as cache hits, and jobs whose artifacts are pruned transition to `expired`.

Each completed job also records `execution_duration_ms`, measured inside the worker
process around the scientific workflow itself. The job API returns this value together
with `cache_hit` and `cache_hit_count`, allowing cold execution and cached retrieval to
be compared without mixing UI rendering time into the measurement.

## Startup Readiness

Before loading the full Streamlit workspace, the packaged entrypoint starts or contacts
the local backend and validates its `/health` service identity and application version.
If readiness fails, the UI remains usable but displays a warning that backend-powered
workflows are offline, including the backend log location in the diagnostic details.

## What Still Needs To Move

Reusable export generation and the individual trajectory-analysis calculations remain candidates for later backend expansion. Archive validation and trajectory inventory now run behind the backend contract.

## Current Architectural Rule Of Thumb

When a workflow:

- parses large uploaded files
- builds a reusable intermediate table or artifact
- is expensive enough to feel slow on rerun
- or is likely to be reused by another UI later

it should move toward:

1. a Streamlit-free helper in `src/hps/core/` or a backend-oriented service module
2. a registered backend workflow in `src/hps/services/backend_jobs.py`
3. a validated request schema in `src/hps/api/schemas.py`
4. a thin Streamlit submission/rendering layer in `src/hps/ui/app_main.py`

## Tracking The Remaining Work

The active development checklist lives in [TODO.md](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/TODO.md).

Shared UI-side request signatures, polling, cached result state, and uploaded-file serialization now live in `hps.ui.backend_workflows`. Workspace renderers should use that module rather than adding new polling loops to `app_main.py`.
