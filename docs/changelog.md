# Changelog

## Unreleased

### Documentation

- Refreshed the screenshot gallery for the redesigned landing page and workspaces.
- Added the registry-driven Feature Map screenshot to the README and navigation guide.
- Removed the stale, manually duplicated feature-map document and updated current guides to match the live interface and workspace modules.

## 0.2.0 - 2026-08-07

### Electronic workspace and UI improvements

- Refined the `Electronic` workspace so `Bands and Spin` and `Advanced` reflect the current tool grouping.
- Updated the Electronic tool selector to use radio buttons for a cleaner, faster-switching workflow.
- Expanded the bandstructure workflow into `Band Structure Studio`.
- Added multi-dataset legend labels for bandstructure comparison plots.
- Fixed multi-dataset bandstructure uploads so each dataset uses unique Streamlit widget keys.
- Added optional k-path segment filtering for bandstructure plots.
- Added optional x-axis label offsets for selected k-point labels.
- Added PNG and PDF export actions for generated bandstructure plots.
- Added Brillouin-zone plotting from uploaded `geometry.in` data.
- Added interactive 3D Brillouin-zone rendering with k-path overlays from `control.in` when available.
- Added PNG and PDF export actions for Brillouin-zone plots.
- Reworked the bandstructure module UI into tabs, grouped controls, advanced settings, and export sections.
- Added expandable dataset summary cards with file-detection status plus VBM/CBM and band-gap details.
- Replaced the older purple divider-style section headers across the app with consistent card-style section headers.
- Moved several section-level helper texts into the new card headers for a cleaner, more consistent layout.
- Added dedicated documentation for the bandstructure module in [docs/features/band-structure-studio.md](features/band-structure-studio.md).
- Linked the new bandstructure documentation from [docs/index.md](index.md) and [docs/features/electronic-workspace.md](features/electronic-workspace.md).
- Cleaned up `molecule_builder.py`, `pdf_analysis.py`, `electronic_property.py`, and `md_analysis.py` to reduce dead code, duplicate imports, and legacy side effects.

### Workspace redesign

- Reworked the app around a landing page plus workspace cards instead of the older always-on, sidebar-first flow.
- Moved structure upload into `Structure -> Overview`.
- Added a `Current Structure` summary card scoped to the Structure workspace.
- Added an optional `Browse feature map` tree for navigating the full tool surface.
- Introduced a shared navigation registry in [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py) so the visible selectors and feature map stay aligned.
- Stopped writing labelled uploaded structures into the repo root during initialization.

### Backend modernization and release readiness

- Added redistributable, checksum-validated scientific regression data for Structure,
  PDOS, band structure, spin texture, and a centered 50 fs molecular-dynamics slice.
- Added provenance-aware guided Structure, Electronic, and Dynamics projects that can
  be listed and bundled with the `hps-examples` command.
- Added backend version-readiness checks, cache and execution timing metrics, trajectory
  artifact exports, retention rules, and stale-job recovery.
- Added automated Streamlit startup/navigation smoke coverage and a browser-driven
  release acceptance workflow.
- Strengthened lint checks for the maintained package layers and applied consistent
  formatting across those layers.
- Split the remaining Structure, Electronic, Dynamics, and Utilities renderers out of `app_main.py`, leaving it as the workspace coordinator.
- Added backend PDF simulation, bandstructure parsing, spin-texture parsing, and trajectory archive preprocessing contracts.
- Added artifact-size retention, stale-job recovery, cache-hit accounting, and missing-artifact cache safeguards.
- Replaced unrestricted dataset-expression evaluation with an allowlisted mathematical expression engine.
- Added safe trajectory ZIP extraction with traversal, symlink, file-count, and expanded-size protections.
- Added backend upload and numerical range validation.
- Removed the broken legacy geometry-ZIP action after the unlicensed external Perl helper
  was removed from the public repository; trajectory analysis continues through validated
  uploaded ZIP archives.
- Added CI, reproducible release checks, strict documentation builds, and package build verification.
- Added public contribution, conduct, security, and citation metadata.
- Made package imports safe in headless environments by removing eager tool imports and import-time plotting during tests.
- Replaced dynamic module namespace injection with explicit UI and structure-domain dependencies, allowing static undefined-name checks to cover the main application.
- Extracted reusable backend workflow state, polling, and file-payload helpers from the Streamlit monolith.
- Fixed the Structure ADP workflow to read the active uploaded structure instead of an undefined file buffer.
- Extracted Structure upload state, backend-summary lifecycle, current-structure metadata, downloads, details, and viewer rendering into a dedicated workspace package.
- Extracted Structure navigation into a typed selection model and moved symmetry and PXRD renderers out of the monolithic app module.
- Fixed publication PXRD d-spacing ticks for plots using the backend's `q (A^-1)` result label.
- Moved the Structure PDF workflows and reduced-PDF parsing into a focused analysis module, removed an unreachable duplicate conversion implementation, and made temporary CIF cleanup automatic.
- Extracted and tested the adjacent Bader charge-analysis parsers, including atom-ID ranges and integrated-property tables.
- Extracted atomic-distance, distortion, lattice percentage-deviation, and ADP workflows into the Structure analysis package.
- Added isolated upload-state keys for lattice deviation, preventing collisions with Structure interpolation uploads.
- Extracted rotation, reflection, translation, deletion, labelling, and interpolation renderers from the application coordinator.
- Made structure mutation explicit by returning updated structures from transformation renderers.
- Fixed transformation output filenames that previously depended on unrelated workflow-local state.
- Prevented one-image rotation interpolation from dividing by zero and guarded unmatched or incomplete structure interpolation inputs.
- Removed a fully commented-out legacy transformation prototype.
- Renamed the app-facing product name to `Hybrid Perovskite Studio`.
- Added feature-oriented documentation under `docs/features/`.
- Added a `PXRD Analysis` workflow to the `Structure` workspace using `pymatgen` for simulated powder X-ray diffraction.
- Added manual `2theta` and `q` range entry, optional Bragg-reflection overlays, optional `d`-spacing top axes, and optional experimental PXRD comparison uploads including `.chi` files.
- Added normalization and x-range clipping for simulated versus experimental PXRD comparisons.
- Added publication-style PDF export for PXRD plots with Matplotlib.
- Added a Structure Workspace labelling tool that exports custom-labelled `geometry.in` files for one or more selected molecule groups.
- Updated the labelling export so non-selected atoms keep their plain element symbols while selected atoms receive user-defined labels.
- Updated AIMS-format labelling exports to preserve the original uploaded `geometry.in` line structure when only atom labels change.
- Added an interactive 3D spin-texture workflow to the `Electronic` workspace with plane-aware `xy`/`yz`/`xz` handling aligned to the 2D spin-texture parser.
- Added reciprocal-space scaling for 3D spin texture from optional uploaded `geometry.in` files.
- Added single-bundle file upload detection for 3D spin texture, including automatic detection of `spin_texture.dat`, `geometry.in`, `.out`, and preset `.json` files.
- Added reusable 3D spin-texture presets for reapplying the same plotting parameters to later datasets.
- Added multiple 3D spin-texture colormap choices plus color modes for normalized component, raw component, and total spin magnitude.
- Added 3D spin-texture controls for per-state opacity, energy-axis range, text size, and background-grid visibility.
- Expanded the 3D spin-texture viewing area and isolated the plot canvas from the Streamlit app theme with a white background.
- Removed the temporary editable-PDF export action from the 3D spin-texture workflow and kept HTML plus preset export actions.
- Added regression tests covering reciprocal-lattice scaling and shared 2D/3D plane mapping for electronic spin-texture parsing.
