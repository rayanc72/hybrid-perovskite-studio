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
- `electronic_pdos`
  - used for PDOS file-role detection, parsing, table generation, and combination preparation
- `md_parse`
  - used for parsing AIMS MD output files into tabular timeseries data

## Why This Matters

These migrations reduce repeated parsing work inside `src/hps/ui/app_main.py` and make it possible to:

- reuse cached results for repeated inputs
- move long-running work off the most fragile rerun paths
- expose stable backend contracts for future UI refactors
- profile execution in a more controlled service layer

## What Still Needs To Move

The largest remaining candidates are:

- Structure/PDF analysis workflows
- zipped trajectory-analysis workflows in the Dynamics workspace
- additional electronic workflows such as bandstructure and spin-texture preprocessing
- export generation that still happens directly in Streamlit

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
