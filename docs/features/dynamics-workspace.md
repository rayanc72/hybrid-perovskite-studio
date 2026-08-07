# Dynamics Workspace

## Overview

The Dynamics workspace supports both direct AIMS MD output analysis and deeper trajectory analysis from uploaded archives.

## Where It Appears In The UI

- Start page workspace card: `Dynamics`
- Workspace views:
  - `Analyze AIMS MD output`
  - `Trajectory analysis`

## Analyze AIMS MD Output

This view is designed for direct processing of uploaded AIMS MD output files.

Capabilities:

- parse uploaded MD output files
- plot extracted MD data
- export parsed results as CSV
- generate geometry/archive outputs through the Perl helper

## Trajectory Analysis

This view expects a zipped trajectory directory and a timestep value. Once loaded, users can choose from several trajectory analyses:

- H-Bond Analysis
- Distance Analysis
- Average Structure
- Distortion Analysis
- Pair Distribution Function
- Anisotropic Displacement Parameter

## Typical Workflow

1. Open the `Dynamics` workspace.
2. Choose either `Analyze AIMS MD output` or `Trajectory analysis`.
3. Upload the expected file type for that path.
4. Enter any analysis-specific settings.
5. Run the workflow and inspect plots, tables, or downloads.

## Inputs

- For direct MD output:
  one or more `.out` files
- For trajectory analysis:
  a zipped directory plus timestep
- Additional analysis-specific inputs such as:
  - donor/acceptor atoms
  - cutoffs
  - time ranges
  - atom symbols
  - bin counts

## Outputs

- Plotly charts
- Data tables
- CSV export
- Generated geometry ZIP output
- Average-structure export

## Notes And Limitations

- MD workflows depend on optional MDAnalysis-related packages.
- Trajectory analysis assumes specific input conventions for extracted frame data.
- The helper script [create_geometry_zip.pl](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/create_geometry_zip.pl) remains part of the direct MD-output path.

## Code Touchpoints

- UI:
  [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/app_main.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py)
- MD logic:
  [src/hps/domain/md_analysis.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/domain/md_analysis.py)
- Helper script:
  [create_geometry_zip.pl](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/create_geometry_zip.pl)

## Last Verified

- Date: 2026-03-19
