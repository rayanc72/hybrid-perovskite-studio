# Structure Workspace

## Overview

The Structure workspace is the entry point for uploaded crystal structures. It combines structure loading, inspection, analysis, transformation, export, PXRD simulation, and PDF simulation in a single workspace.

## Where It Appears In The UI

- Landing-page workspace: `Structure`
- Workspace views:
  - `Analysis`
  - `Transformations`

## Main Workflow

1. Open the `Structure` workspace from the landing page.
2. Upload a structure file in `.in`, `.cif`, or `.next_step` format using the upload box at the top of the workspace.
3. Review the `Current Structure` summary.
4. Move to `Analysis` or `Transformations` depending on your task.
5. Export geometry or labelled structure files from the summary or downstream tools, including custom-labelled `geometry.in` exports for selected molecules.

The workspace opens with no view selected. The current structure summary and its
collapsible details remain available until you choose `Analysis` or `Transformations`.

## Structure Upload

The upload box remains visible above the current structure summary in both workspace views.

Key actions:

- Upload a structure file
- Replace the current structure by uploading a new one
- Remove the current structure from the session
- Review the currently loaded file name

Current behavior:

- The uploaded structure is stored in Streamlit session state as raw bytes and reparsed on reruns.
- The app no longer writes a labelled structure file into the repo root during upload.

## Current Structure Summary

When a structure is loaded, the workspace shows a persistent summary directly below the upload box and above the view controls, with:

- file name
- detected format
- atom count
- bonded-group count (finite molecules and periodic networks)
- download button for the current AIMS geometry
- download button for the labelled structure
- remove-current-structure action
- optional symmetry details
- a collapsible `Molecule groups and names` listing with original group numbers, finite-molecule or periodic-network classification, and atom names such as `C1` and `H2`
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

Each transformation offers a CIF download alongside its AIMS geometry download.
Rotation batches and interpolation series offer a separate ZIP of CIF files.
CIF conversion and CIF ZIP creation run only when their download button is clicked,
using the generated structures without rerunning the transformation. Custom molecule
labels are retained in CIF site names, with atom indices added to keep them unique.

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
- On-demand CIF downloads and CIF ZIP archives for transformed structures
- Labelled structure downloads
- Custom-labelled `geometry.in` exports for one or more selected molecules
- Tables of structural metrics
- Plotly and Matplotlib plots
- Publication-style PXRD PDF plot downloads
- ZIP archives for generated structure series

## Notes And Limitations

- Detected molecules are geometric bonded groups, including isolated atoms and
  periodic inorganic networks; they are not validated chemical molecule identities.
  Structure details distinguish finite groups from 1D, 2D, and 3D networks.
  Backend and UI use the same detector, respecting the structure's periodic axes
  and excluding configured element pairs in either order.
- A bond is detected when the distance is strictly below the sum of ASE covalent
  radii and per-atom tolerances: 0.1 Å for C/H/N/O/S, 0.5 Å for Cl, and
  0.25 Å plus configured bond padding for other elements. Padding does not change
  the C/H/N/O/S/Cl tolerances. Detection and reconstruction share these criteria.
- Molecular coordinates are unwrapped by accumulating the lattice-image shifts
  stored on bonds. A boundary-crossing molecule remains finite when every cycle
  closes in the same image. Nonzero cycle translations identify periodic networks;
  the number of independent translations determines their dimension.
- Rotation, reflection, center-of-mass, and dipole analysis select finite groups
  using their original group numbers. Periodic networks remain available for
  group labelling, translation, and deletion, but cannot be reconstructed as a
  finite molecule. Single isolated atoms count as finite groups.
- Unwrapping anchors the first selected atom in its supplied image, preserves atom
  order, supports skewed cells and partial periodic boundaries, and leaves the
  input structure unchanged. Rebuild graphs after changing coordinates or bonds.
  Classification depends on the configured geometric bond thresholds; it does
  not establish chemical identity or bond order.
- PXRD broadening is currently specified in degrees of `2theta`, even when the displayed x-axis is `q`.
- PDF analysis uses a short-lived temporary directory when converting the active structure for DiffPy and cleans it automatically after calculation.
- The 3D viewer is opt-in and can be heavier than the basic export paths.
- Custom molecule labelling preserves non-selected atom symbols as plain element labels in the exported `geometry.in`.

## Last Verified

- Application baseline: [GitHub v0.3.0](https://github.com/rayanc72/hybrid-perovskite-studio/releases/tag/v0.3.0)
- Documentation reviewed: 2026-11-22
