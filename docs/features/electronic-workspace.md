# Electronic Workspace

## Overview

The Electronic workspace focuses on plotting and inspecting electronic-structure outputs. It groups band, spin, PDOS, polarization, and absorption workflows under one workspace.

## Where It Appears In The UI

- Landing-page workspace: `Electronic`
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

For a complete band workflow, follow the [bands and Excel tutorial](../tutorials/bands.md).
See [input conventions](../reference/input-formats.md#electronic-data) for band, PDOS, and spin data.

## Outputs

- Plotly plots
- Matplotlib plots
- Parsed data tables
- Downloadable HTML plot exports
- Downloadable preset JSON exports
- Band Structure Studio PNG/PDF figures and momentum–energy `.xlsx` workbooks
- Direct no-SOC band-file support and multi-dataset SOC/no-SOC comparisons

## Notes And Limitations

- The 3D spin-texture workflow currently restores saved plot parameters, but not a manually rotated in-browser camera angle.

## Last Verified

- Application baseline: [GitHub v0.3.0](https://github.com/rayanc72/hybrid-perovskite-studio/releases/tag/v0.3.0)
- Documentation reviewed: 2026-11-22
