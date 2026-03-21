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
- Plot partial density of states (PDOS)

### Advanced

- Plot polarization
- Plot absorption spectra

## Typical Workflow

1. Open the `Electronic` workspace.
2. Choose the relevant view.
3. Select the target tool from the `Tool` selector.
4. Upload the required output file or file set.
5. Configure plot settings, state ranges, or formatting.
6. Generate the visualization and download any resulting output.

## Inputs

- Text or data outputs from electronic-structure calculations
- Optional companion `.out` files for metadata in some spin workflows
- Plot configuration values such as:
  - state ranges
  - axis limits
  - energy shifts
  - labels
  - export settings

## Outputs

- Plotly plots
- Matplotlib plots
- Parsed data tables
- Downloadable plot exports

## Notes And Limitations

- Several plotting flows still rely on legacy-style helper functions living in the main UI module and domain wrappers.
- Some exports depend on optional plotting/image backends.
- The current navigation is registry-driven, but the underlying tool implementations are still mostly imperative.

## Code Touchpoints

- UI:
  [src/hpame/ui/app_main.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/app_main.py)
- Navigation registry:
  [src/hpame/ui/navigation.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/navigation.py)
- Electronic logic:
  [src/hpame/domain/electronic_property.py](/Users/rayanchakraborty/hPAME/src/hpame/domain/electronic_property.py)
- Tool helpers:
  [src/hpame/tools/plot_band.py](/Users/rayanchakraborty/hPAME/src/hpame/tools/plot_band.py)
  [src/hpame/tools/scan_cbm.py](/Users/rayanchakraborty/hPAME/src/hpame/tools/scan_cbm.py)

## Last Verified

- Date: 2026-03-19
