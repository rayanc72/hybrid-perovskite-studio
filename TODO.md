# HPS Development TODO

This file is the working checklist for the backend modernization and performance-improvement effort.

## Public Release Readiness

- [x] Add a reproducible local release-check command
- [x] Add continuous integration for tests, modern-layer lint, docs, and package builds
- [x] Replace unrestricted dataset-expression evaluation
- [x] Harden uploaded trajectory ZIP extraction
- [x] Add backend upload and numerical input bounds
- [x] Add contribution, conduct, security, and citation files
- [x] Remove dynamic namespace injection from packaged application modules
- [x] Extract shared backend workflow state and polling helpers from `src/hps/ui/app_main.py`
- [x] Extract Structure upload, summary, and current-structure overview rendering
- [x] Extract Structure navigation plus symmetry and PXRD rendering
- [x] Extract Structure PDF rendering and charge-analysis parsers
- [x] Extract Structure distance, distortion, lattice-deviation, and ADP rendering
- [x] Extract all Structure transformation rendering
- [x] Split workspace rendering out of `src/hps/ui/app_main.py`
- [x] Add redistributable scientific regression fixtures and expected numerical results
- [x] Add artifact retention and stale-job recovery policies
- [ ] Add guided example projects and provenance-aware project bundles

## In Progress

- [x] Finish migrating the Structure workspace’s PDF/RDF simulation and comparison paths
- [ ] Keep the Streamlit UX stable while replacing direct rerun-heavy execution with backend jobs

## Backend Foundation

- [x] Add local backend service entrypoint and health endpoint
- [x] Add SQLite-backed job and artifact persistence
- [x] Add reusable job submission, polling, and artifact retrieval helpers
- [x] Add a Python 3.11 development environment that can run the backend tests
- [x] Add explicit backend artifact types and retention/cleanup rules
- [ ] Add profiling hooks for migrated workflows

## Structure Workspace

- [x] Migrate structure upload summary / structure context
- [x] Migrate symmetry sweep generation
- [x] Migrate PXRD preprocessing and profile generation
- [x] Migrate PDF simulation preprocessing and reusable intermediate outputs
- [x] Migrate RDF/PDF comparison preprocessing where feasible
- [ ] Move more structure-derived tables out of `st.session_state`
- [ ] Add backend support for reusable downloadable structure artifacts where it reduces rerun cost

## Electronic Workspace

- [x] Migrate PDOS parsing and table generation
- [ ] Migrate PDOS export preparation if static exports remain expensive
- [x] Migrate bandstructure file parsing and reusable segment data
- [x] Migrate spin-texture parsing for both 2D and 3D renderers
- [x] Standardize plot-ready response contracts across PDOS and bandstructure workflows

## Dynamics Workspace

- [x] Migrate AIMS MD output parsing
- [x] Migrate zipped trajectory validation and frame preprocessing into backend jobs
- [x] Migrate reusable trajectory inventory and frame-metric generation
- [ ] Replace long-lived Streamlit cache/state for trajectory analysis with backend-managed caching
- [ ] Add backend artifact generation for reusable CSV/structure outputs from trajectory workflows

## UI Cleanup

- [x] Extract shared backend job submission/polling UI helpers from `src/hps/ui/app_main.py`
- [ ] Extract shared result rendering blocks for backend-returned tables and plot data
- [ ] Reduce the number of workflow-specific session-state keys in `src/hps/ui/app_main.py`
- [ ] Stop adding new heavy scientific logic directly to the UI module

## Testing And Validation

- [x] Add backend store tests
- [x] Add backend API contract tests for migrated workflows
- [x] Add Streamlit-free core workflow tests for migrated helpers
- [x] Add regression fixtures for realistic Structure, PDOS, and MD inputs
- [ ] Add startup validation that confirms Streamlit can reach the local backend
- [ ] Add performance checks for first-run vs cached-run latency

## Documentation

- [x] Document the current backend architecture
- [x] Document the current modernization status and migrated workflows
- [x] Create a living TODO tracker
- [x] Keep workspace docs in sync as more workflows move behind the backend

## Later / Deferred

- [ ] Profile migrated workflows before choosing any Rust/PyO3 target
- [ ] Evaluate Rust only for stable post-migration hotspots
