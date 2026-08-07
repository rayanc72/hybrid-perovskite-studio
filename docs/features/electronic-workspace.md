# Electronic Workspace

## Overview

The Electronic workspace focuses on plotting and inspecting electronic-structure outputs. It groups band, spin, PDOS, polarization, and absorption workflows under one workspace.

## Where It Appears In The UI

- Start page workspace card: `Electronic`
- Workspace views:
  - `Bands and Spin`
  - `Advanced`

## Main Tools

### Bands and Spin

- Plot bandstructure
- Plot spin texture
- Plot 3D spin texture
- Plot partial density of states (PDOS)
- Detailed module guide:
  [Band Structure Studio](band-structure-studio.md)

### 3D Spin Texture Highlights

- Single multi-file upload that detects `spin_texture.dat`, optional `geometry.in`, optional `.out`, and optional preset `.json`
- Plane-aware 3D rendering for `xy`, `yz`, and `xz` spin-texture datasets
- Interactive Plotly surface with selectable colormaps
- Surface coloring by normalized component, raw component, or total spin magnitude
- Per-state opacity controls plus optional energy-axis range limits
- Reusable view presets that can be applied to later datasets
- HTML export for interactive sharing

### Advanced

- Plot polarization
- Plot absorption spectra

## Typical Workflow

1. Open the `Electronic` workspace.
2. Choose the relevant view.
3. Select the target tool from the `Tool` selector.
4. Upload the required output file or file set.
5. For 3D spin texture, confirm the detected file roles and optionally load a saved preset.
6. Configure state ranges, plane selection, colormap, color mode, opacity, and energy-axis limits.
7. Generate the visualization and download any resulting output.

## Inputs

- Text or data outputs from electronic-structure calculations
- Optional companion `.out` files for metadata in some spin workflows
- Optional `geometry.in` files for reciprocal-space scaling in the 3D spin-texture workflow
- Optional preset `.json` files to restore a previous 3D spin-texture configuration
- Plot configuration values such as:
  - plane selection (`xy`, `yz`, `xz`)
  - state ranges
  - state-specific opacities
  - energy-axis limits
  - energy shifts
  - colormap and color mode
  - text size and background-grid visibility
  - export settings

## Outputs

- Plotly plots
- Matplotlib plots
- Parsed data tables
- Downloadable HTML plot exports
- Downloadable preset JSON exports

## Notes And Limitations

- Several plotting flows still rely on legacy-style helper functions living in the main UI module and domain wrappers.
- The 3D spin-texture workflow currently restores saved plot parameters, but not a manually rotated in-browser camera angle.
- The current navigation is registry-driven, but the underlying tool implementations are still mostly imperative.

## Code Touchpoints

- UI:
  [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py)
- Electronic logic:
  [src/hps/domain/electronic_property.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/electronic_property.py)
- Tool helpers:
  [src/hps/tools/plot_band.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/tools/plot_band.py)
  [src/hps/tools/scan_cbm.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/tools/scan_cbm.py)

## Last Verified

- Date: 2026-04-03
