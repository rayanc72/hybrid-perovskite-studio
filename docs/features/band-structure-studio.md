# Band Structure Studio

## Overview

- `Band Structure Studio` lives in the `Electronic` workspace.
- It combines two related outputs:
  - `Band Structure`
  - `Brillouin Zone`
- It supports single-dataset and multi-dataset workflows.
- It is designed for uploaded FHI-aims output files.

## Where It Appears

- Workspace: `Electronic`
- View: `Bands and Spin`
- Tool: `Plot bandstructure`

## Core Purpose

- Plot one or more band structures.
- Align band energies relative to the detected VBM.
- Compare multiple datasets in one figure.
- Restrict the plot to selected k-path segments.
- Visualize the Brillouin zone from the uploaded lattice.
- Overlay the uploaded band path on the Brillouin-zone view.

## Required Files

- For band structure plotting:
  - `band*.out`
- For Brillouin-zone plotting:
  - `geometry.in`
- For x-axis path labels and k-path reconstruction:
  - `control.in`

## Inputs

- Number of datasets:
  - integer
  - allowed range in UI: `1` to `10`
- Per dataset:
  - one multi-file uploader
  - color text input
  - legend label text input

## Per-Dataset Upload Behavior

- Each dataset is uploaded independently.
- Each dataset gets its own widget key.
- This avoids duplicate Streamlit widget-key errors.
- The uploader accepts multiple files at once.
- The module looks for:
  - `band*.out`
  - `geometry.in`
  - `control.in`

## Automatic Dataset Summary

- Uploaded datasets are summarized in the `Loaded Data Sets` expander.
- Each summary card includes:
  - legend label
  - selected color
  - number of detected `band*.out` files
  - whether `geometry.in` was found
  - whether `control.in` was found
  - VBM state
  - VBM k-point coordinate
  - VBM energy
  - CBM state
  - CBM k-point coordinate
  - CBM energy
  - band gap

## Band-Edge Detection

- The module scans the uploaded `band*.out` files for each dataset.
- It computes:
  - VBM information
  - CBM information
- The detected VBM energy is used as the dataset energy shift.
- This makes the plotted VBM align to `0 eV`.

## Band Structure Tab

- Main purpose:
  - generate the bandstructure figure
- Main controls:
  - energy-axis range slider
  - `Generate Band Structure` button
- Advanced controls:
  - k-path segment selection
  - x-axis label offsets
  - optional x-axis scaling to match the first dataset

## Band Structure Plot Features

- Supports one dataset or multiple datasets.
- Uses the selected dataset colors.
- Uses the selected legend labels.
- Draws vertical path-divider lines.
- Draws a horizontal reference line at `0 eV`.
- Shows a legend automatically when more than one dataset is plotted.
- Keeps the legend inside the plot area.
- Uses a white legend background and smaller text.

## Multi-Dataset Comparison

- Multiple datasets can be plotted together.
- Each dataset can have:
  - its own color
  - its own legend label
- Optional scaling can match the x-axis length to the first dataset.
- When scaling is enabled:
  - later datasets are rescaled to the first dataset’s total k-path length
- When scaling is disabled:
  - each dataset keeps its own native path length

## K-Path Segment Filtering

- The user can optionally restrict the plotted path.
- Input format:
  - one-based indices
  - comma-separated values
  - ranges allowed
- Example:
  - `1,3,5-6`
- Blank input means:
  - plot all segments
- Validation behavior:
  - negative or zero indices are rejected
  - descending ranges are rejected
  - non-existent segments raise a user-visible error

## X-Axis Label Offsets

- The user can optionally offset selected k-point labels.
- Purpose:
  - reduce label crowding
  - improve readability for dense paths
- Input format:
  - `label_index:offset`
  - comma-separated list
- Example:
  - `2:-0.08, 5:-0.15`
- Behavior:
  - works on selected x-axis labels only
  - applies in scaled and unscaled workflows

## Export For Band Structure

- Export section appears below a generated plot.
- Buttons are shown side by side.
- Available exports:
  - `PNG`
  - `PDF`
- The PDF export is suitable for later editing in vector-friendly tools.

## Brillouin Zone Tab

- Main purpose:
  - plot the Brillouin zone for one selected dataset
- Main controls:
  - dataset selector
  - `Generate Brillouin Zone` button
- Dataset selection is useful when multiple datasets are uploaded.

## Brillouin Zone Construction

- The Brillouin zone is built from `geometry.in`.
- The reciprocal lattice is computed from the uploaded lattice vectors.
- The first Brillouin zone is constructed by Voronoi analysis in reciprocal space.

## Brillouin Zone Plot Features

- The plot is interactive.
- It uses Plotly 3D rendering.
- The user can:
  - rotate
  - zoom
  - pan
- It shows:
  - Brillouin-zone edges
  - reciprocal lattice vectors
  - reciprocal-vector labels
- If `control.in` is available, it also shows:
  - uploaded k-path segments
  - k-point labels

## Brillouin Zone Styling

- Background grid planes are hidden.
- Scene grids are disabled.
- The figure is enlarged for readability.
- Title and axis text are larger than the default.
- K-point and reciprocal-vector labels use larger text.
- The goal is a cleaner, more focused reciprocal-space view.

## Export For Brillouin Zone

- Export section appears below a generated Brillouin-zone plot.
- Buttons are shown side by side.
- Available exports:
  - `PNG`
  - `PDF`

## Reset Behavior

- `Clear files` resets the bandstructure upload widgets.
- This increments the uploader generation key.
- It forces Streamlit to treat future uploads as a new session of upload controls.

## Error Handling

- Invalid k-path segment input shows a user-facing error.
- Invalid label-offset input shows a user-facing error.
- Missing `geometry.in` blocks Brillouin-zone generation.
- Missing `control.in` prevents path-label reconstruction.
- Missing `band*.out` prevents useful band plotting.

## Current Implementation Notes

- Bandstructure plotting uses Matplotlib.
- Brillouin-zone plotting uses Plotly.
- The module combines UI logic in:
  - [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py)
- Domain and plotting helpers live in:
  - [src/hps/domain/electronic_property.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/electronic_property.py)

## Typical Workflow

- Open `Electronic`.
- Choose `Bands and Spin`.
- Choose `Plot bandstructure`.
- Set the number of datasets.
- Upload files for each dataset.
- Optionally inspect `Loaded Data Sets`.
- Open `Band Structure`:
  - set plot range
  - optionally edit advanced settings
  - generate the plot
  - export as `PNG` or `PDF`
- Open `Brillouin Zone`:
  - select a dataset
  - generate the plot
  - export as `PNG` or `PDF`

## Last Verified

- Date: 2026-03-20
