# Structure Workspace

## Overview

The Structure workspace is the entry point for uploaded crystal structures. It combines structure loading, inspection, analysis, transformation, export, and PDF simulation in a single workspace.

## Where It Appears In The UI

- Start page workspace card: `Structure`
- Workspace views:
  - `Overview`
  - `Analysis`
  - `Transformations`

## Main Workflow

1. Open the `Structure` workspace from the landing page.
2. In `Overview`, upload a structure file in `.in`, `.cif`, or `.next_step` format.
3. Review the `Current Structure` summary card.
4. Move to `Analysis` or `Transformations` depending on your task.
5. Export geometry or labelled structure files from the summary card or downstream tools, including custom-labelled `geometry.in` exports for selected molecules.

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

## Current Structure Card

When a structure is loaded, the workspace shows a persistent summary card with:

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

`Analysis` is grouped into four sections:

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
- ZIP archives for generated structure series

## Notes And Limitations

- Several tools remain implemented directly inside [src/hps/ui/app_main.py](../../src/hps/ui/app_main.py), so UI and scientific logic are still closely coupled.
- PDF analysis still creates temporary files during calculation, but upload itself no longer leaves labelled structure files in the repo root.
- The 3D viewer is opt-in and can be heavier than the basic export paths.
- Custom molecule labelling preserves non-selected atom symbols as plain element labels in the exported `geometry.in`.

## Code Touchpoints

- UI and routing:
  [src/hps/ui/app_main.py](../../src/hps/ui/app_main.py)
- Navigation registry:
  [src/hps/ui/navigation.py](../../src/hps/ui/navigation.py)
- Structure logic:
  [src/hps/domain/structure_manager.py](../../src/hps/domain/structure_manager.py)
- Molecule helpers:
  [src/hps/domain/molecule_builder.py](../../src/hps/domain/molecule_builder.py)
- PDF logic:
  [src/hps/domain/pdf_analysis.py](../../src/hps/domain/pdf_analysis.py)

## Last Verified

- Date: 2026-04-01
