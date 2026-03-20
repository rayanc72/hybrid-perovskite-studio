# Changelog

## 2026-03-19

- Reworked the app around a landing page plus workspace cards instead of the older always-on, sidebar-first flow.
- Moved structure upload into `Structure -> Overview`.
- Added a `Current Structure` summary card scoped to the Structure workspace.
- Added an optional `Browse feature map` tree for navigating the full tool surface.
- Introduced a shared navigation registry in [src/hpame/ui/navigation.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/navigation.py) so the visible selectors and feature map stay aligned.
- Stopped writing labelled uploaded structures into the repo root during initialization.

## Unreleased

- Renamed the app-facing product name to `Hybrid Perovskite Studio`.
- Reorganized the codebase under `src/hpame/` with archived compatibility shims in `legacy_shims/`.
- Added feature-oriented documentation under `docs/features/`.
