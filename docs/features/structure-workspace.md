# Structure Workspace

## Overview

The Structure workspace is the entry point for uploaded crystal structures. It combines structure loading, inspection, analysis, transformation, export, PXRD simulation, and PDF simulation in a single workspace.

## Where It Appears In The UI

- Landing-page workspace: `Structure`
- Workspace views:
  - `Overview`
  - `Analysis`
  - `Transformations`

## Main Workflow

1. Open the `Structure` workspace from the landing page.
2. In `Overview`, upload a structure file in `.in`, `.cif`, or `.next_step` format.
3. Review the `Current Structure` summary.
4. Move to `Analysis` or `Transformations` depending on your task.
5. Export geometry or labelled structure files from the summary or downstream tools, including custom-labelled `geometry.in` exports for selected molecules.

## Overview View

The `Overview` view is where users load and manage the active structure.

Key actions:

- Upload a structure file
- Replace the current structure by uploading a new one
- Remove the current structure from the session
- Review the currently loaded file name

Current behavior:

- The uploaded structure is stored in Streamlit session state as raw bytes and reparsed on reruns.
- The app no longer writes a labelled structure file into the repo root during upload.

## Current Structure Summary

When a structure is loaded, the workspace shows a persistent summary with:

- file name
- detected format
- atom count
- molecule-group count
- download button for the current AIMS geometry
- download button for the labelled structure
- remove-current-structure action
- optional symmetry details
- optional detected-molecule listing
- optional 3D viewer

## Analysis View

`Analysis` is grouped into five sections:

### Symmetry

- Symmetrize structure
- Anisotropic displacement parameters
- Calculate polarization direction

### Molecules

- Find center of mass
- Calculate dipole moment
- Charge analysis

### Structure Metrics

- Calculate atomic distances
- Calculate octahedral distortions
- Calculate percentage deviation

### PXRD Analysis

- Simulate PXRD
  - Set the X-ray wavelength
  - Enter the range manually in `2theta` or `q`, matching the selected x-axis
  - Apply optional FWHM peak broadening in degrees of `2theta`
  - Plot the x-axis in `2theta` or `q`
  - Optionally overlay Bragg reflections
  - Optionally show a top `d`-spacing axis on the displayed and downloaded plots
  - Optionally upload experimental PXRD data for comparison
  - Accept common two-column text formats including `.chi`
  - Clip uploaded experimental data to the simulated x-axis range
  - Normalize simulated and experimental intensities before plotting when comparison data is present
  - Download a publication-style PDF plot

### PDF Analysis

- Simulate PDF
- Plot RDF
- Compare experimental PDF
- Convert reduced PDF to g(r)

Each PDF task opens as its own workflow instead of appearing as an optional section on the same page.

## Transformations View

`Transformations` is grouped into two sections:

### Molecule Operations

- Rotation
  - Rotate Individual Molecules
  - Rotate Multiple Molecules
  - Random Rotation
  - Interpolate by Rotation
  - Rotate Part of Molecules
  - Rotate by Dipole Moment
- Reflection
- Translation
  - Molecules
  - Atoms
- Deletion
- Labelling
  - Select one or more molecule groups
  - Assign an individual label suffix to each selected molecule
  - Export a custom-labelled `geometry.in`
  - Preserve the original uploaded `geometry.in` line structure when possible, changing only the selected atom labels

### Lattice Operations

- Translation
  - Molecules
  - Atoms
- Interpolation

`Interpolation` under lattice operations uses its own multi-file upload workflow.

## Inputs

- Required for most tools:
  one uploaded structure
- Additional optional inputs vary by tool:
  - atom labels
  - molecule-group selections with per-molecule label suffixes
  - Miller indices
  - angles
  - CSV pair definitions
  - custom plotting config
  - experimental PXRD datasets (`.csv`, `.txt`, `.xy`, `.dat`, `.chi`)
  - experimental `.gr` data
  - start and end structures for interpolation/deviation-style workflows

## Outputs

- Structure summaries
- Symmetry metadata
- Molecule listings
- AIMS structure downloads
- Labelled structure downloads
- Custom-labelled `geometry.in` exports for one or more selected molecules
- Tables of structural metrics
- Plotly and Matplotlib plots
- Publication-style PXRD PDF plot downloads
- ZIP archives for generated structure series

## Notes And Limitations

- Structure upload, active-state lifecycle, typed navigation, summary status, metadata, downloads, the initial viewer, analysis workflows, and transformation renderers are implemented under `src/hps/ui/workspaces/structure/`. [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py) coordinates those focused renderers.
- PXRD broadening is currently specified in degrees of `2theta`, even when the displayed x-axis is `q`.
- PDF analysis uses a short-lived temporary directory when converting the active structure for DiffPy and cleans it automatically after calculation.
- The 3D viewer is opt-in and can be heavier than the basic export paths.
- Custom molecule labelling preserves non-selected atom symbols as plain element labels in the exported `geometry.in`.

## Code Touchpoints

- UI and routing:
  [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py)
- Structure overview renderer:
  [src/hps/ui/workspaces/structure/overview.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/overview.py)
- Structure workspace state:
  [src/hps/ui/workspaces/structure/state.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/state.py)
- Structure workspace navigation:
  [src/hps/ui/workspaces/structure/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/navigation.py)
- Symmetry renderer:
  [src/hps/ui/workspaces/structure/analysis/symmetry.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/symmetry.py)
- PXRD renderer and plotting helpers:
  [src/hps/ui/workspaces/structure/analysis/pxrd.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/pxrd.py)
- PDF renderer and reduced-PDF parser:
  [src/hps/ui/workspaces/structure/analysis/pdf.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/pdf.py)
- Charge-analysis parsers:
  [src/hps/ui/workspaces/structure/analysis/charge.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/charge.py)
- Molecule-analysis renderer:
  [src/hps/ui/workspaces/structure/analysis/molecules.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/molecules.py)
- Structure metric renderers and lattice-deviation helpers:
  [src/hps/ui/workspaces/structure/analysis/metrics.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/analysis/metrics.py)
- Rotation workflows:
  [src/hps/ui/workspaces/structure/transformations/rotation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/transformations/rotation.py)
- Reflection, translation, deletion, labelling, and interpolation workflows:
  [src/hps/ui/workspaces/structure/transformations/operations.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/structure/transformations/operations.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py)
- Structure logic:
  [src/hps/domain/structure_manager.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/structure_manager.py)
- Molecule helpers:
  [src/hps/domain/molecule_builder.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/molecule_builder.py)
- PXRD logic:
  [src/hps/domain/structure_manager.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/structure_manager.py)
- PDF logic:
  [src/hps/domain/pdf_analysis.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/pdf_analysis.py)

## Last Verified

- Date: 2026-08-07
