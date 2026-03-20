# Electronic Analysis

## What It Does

The Electronic Analysis section covers visualization and processing of electronic-structure outputs, including polarization plots, PDOS, bandstructure, spin texture, and absorption spectra.

## Where It Appears in the UI

- Sidebar section:
  `Electronic Analysis`
- Current toggles:
  - Plot polarization
  - Plot partial density of states (PDOS)
  - Plot bandstructure
  - Plot spin texture
  - Plot 3D spin texture
  - Plot absorption spectra

## Inputs

- Uploaded text/data files for DOS, bandstructure, spin texture, or absorption workflows
- In some cases, paired files such as geometry/control or optional `.out` files
- Plotting and formatting options provided in the UI

## Outputs

- Plotly and Matplotlib plots
- Data tables for parsed outputs
- Downloadable plot images and data exports

## How To Use It

1. Enable an electronic-analysis toggle in the sidebar.
2. Upload the required output file(s).
3. Configure plot ranges, states, labels, or formatting options.
4. Generate the plot.
5. Download the resulting image or inspect the parsed data table.

## Key capabilities covered here

- Polarization plotting
- Partial density of states plotting
- Bandstructure plotting
- 2D and 3D spin texture views
- Absorption spectra plotting

## Known Limitations

- Some plotting flows still rely on legacy helper modules and tool-style code.
- The current app mixes parsing, plotting, and UI concerns in the same module for some workflows.
- Some advanced exports rely on optional plotting backends and image-generation support.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- Electronic helper logic:
  `src/hpame/domain/electronic_property.py`
- Tool modules:
  `src/hpame/tools/plot_band.py`
  `src/hpame/tools/scan_cbm.py`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
  `src/hpame/domain/electronic_property.py`
  `src/hpame/tools/plot_band.py`
  `src/hpame/tools/scan_cbm.py`
