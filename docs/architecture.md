# Hybrid Perovskite Studio Architecture

## Current layout

The repository now runs from a package-centered layout under `src/hpame/`.

- `src/hpame/app.py` is the supported entrypoint
- `src/hpame/domain/` provides narrow, lazy wrappers around the current scientific modules instead of importing them eagerly at package import time
- `src/hpame/services/runtime.py` owns dependency-group checks and bootstrap behavior
- `src/hpame/io/paths.py` defines shared runtime locations for `output/` and `tmp/`

- `src/hpame/ui/app_main.py` contains the packaged app implementation copied from the legacy entrypoint
- `src/hpame/ui/navigation.py` is the single source of truth for workspace names, workspace descriptions, and the feature-map tree
- `src/hpame/domain/pdf_analysis.py` contains the packaged PDF analysis implementation copied from the legacy module

## Boundaries

### UI layer

Files under `src/hpame/ui/` should contain Streamlit rendering logic, labels, and user-facing messaging.

Navigation-specific guidance:

- [src/hpame/ui/navigation.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/navigation.py) should be updated when workspace structure changes
- [src/hpame/ui/app_main.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/app_main.py) should consume that registry rather than redefining the same tree by hand

### Service layer

Files under `src/hpame/services/` should coordinate app behavior, environment checks, and cross-module orchestration.

### Domain layer

Files under `src/hpame/domain/` should expose scientific operations through narrow interfaces. They should not contain app bootstrap or dependency-install logic.

### IO layer

Files under `src/hpame/io/` should handle repository paths, output conventions, and file/runtime helpers.

## Dependency policy

- `pyproject.toml` is the source of truth for installation metadata
- `requirements.txt` is a compatibility wrapper that installs the editable package with `full` and `dev` extras
- Optional dependency groups are separated by concern: `core`, `md`, `pdf`, `viz`, `auth`
- The current UI requires the `full` stack because of the scientific dependencies used across the packaged modules

## Guardrails

- No wildcard imports in `src/hpame/`
- New package modules should prefer lazy imports when scientific imports are optional or heavy
- Runtime artifacts should go under `output/` or `tmp/`
- New work should target the package tree first
