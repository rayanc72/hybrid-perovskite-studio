# HPS Development TODO

This file is the working checklist for the backend modernization and performance-improvement effort.

## In Progress

- [ ] Finish migrating the Structure workspace’s remaining expensive analysis paths
- [ ] Keep the Streamlit UX stable while replacing direct rerun-heavy execution with backend jobs

## Backend Foundation

- [x] Add local backend service entrypoint and health endpoint
- [x] Add SQLite-backed job and artifact persistence
- [x] Add reusable job submission, polling, and artifact retrieval helpers
- [x] Add a Python 3.11 development environment that can run the backend tests
- [ ] Add explicit backend artifact types and retention/cleanup rules
- [ ] Add profiling hooks for migrated workflows

## Structure Workspace

- [x] Migrate structure upload summary / structure context
- [x] Migrate symmetry sweep generation
- [x] Migrate PXRD preprocessing and profile generation
- [ ] Migrate PDF simulation preprocessing and reusable intermediate outputs
- [ ] Migrate RDF/PDF comparison preprocessing where feasible
- [ ] Move more structure-derived tables out of `st.session_state`
- [ ] Add backend support for reusable downloadable structure artifacts where it reduces rerun cost

## Electronic Workspace

- [x] Migrate PDOS parsing and table generation
- [ ] Migrate PDOS export preparation if static exports remain expensive
- [ ] Migrate bandstructure file parsing and dataset summaries
- [ ] Evaluate spin-texture parsing as the next electronic backend target
- [ ] Standardize plot-ready response contracts across PDOS and bandstructure workflows

## Dynamics Workspace

- [x] Migrate AIMS MD output parsing
- [ ] Migrate zipped trajectory/universe construction into backend jobs
- [ ] Migrate reusable trajectory metric generation
- [ ] Replace long-lived Streamlit cache/state for trajectory analysis with backend-managed caching
- [ ] Add backend artifact generation for reusable CSV/structure outputs from trajectory workflows

## UI Cleanup

- [ ] Extract shared backend job submission/polling UI helpers from `src/hps/ui/app_main.py`
- [ ] Extract shared result rendering blocks for backend-returned tables and plot data
- [ ] Reduce the number of workflow-specific session-state keys in `src/hps/ui/app_main.py`
- [ ] Stop adding new heavy scientific logic directly to the UI module

## Testing And Validation

- [x] Add backend store tests
- [x] Add backend API contract tests for migrated workflows
- [x] Add Streamlit-free core workflow tests for migrated helpers
- [ ] Add regression fixtures for realistic Structure, PDOS, and MD inputs
- [ ] Add startup validation that confirms Streamlit can reach the local backend
- [ ] Add performance checks for first-run vs cached-run latency

## Documentation

- [x] Document the current backend architecture
- [x] Document the current modernization status and migrated workflows
- [x] Create a living TODO tracker
- [ ] Keep workspace docs in sync as more workflows move behind the backend

## Later / Deferred

- [ ] Profile migrated workflows before choosing any Rust/PyO3 target
- [ ] Evaluate Rust only for stable post-migration hotspots
