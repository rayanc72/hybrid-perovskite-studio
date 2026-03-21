# Changelog

## 2026-03-20

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

## 2026-03-19

- Reworked the app around a landing page plus workspace cards instead of the older always-on, sidebar-first flow.
- Moved structure upload into `Structure -> Overview`.
- Added a `Current Structure` summary card scoped to the Structure workspace.
- Added an optional `Browse feature map` tree for navigating the full tool surface.
- Introduced a shared navigation registry in [src/hps/ui/navigation.py](../src/hps/ui/navigation.py) so the visible selectors and feature map stay aligned.
- Stopped writing labelled uploaded structures into the repo root during initialization.

## Unreleased

- Renamed the app-facing product name to `Hybrid Perovskite Studio`.
- Added feature-oriented documentation under `docs/features/`.
