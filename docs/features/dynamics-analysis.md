# Dynamics Analysis

## What It Does

The Dynamics Analysis section supports both direct AIMS MD output analysis and trajectory-based analysis from uploaded archives. It includes hydrogen-bond analysis, time-series plots, RDF workflows, distance analysis, average structures, distortion analysis, and ADP analysis.

## Where It Appears in the UI

- Sidebar section:
  `Dynamics Analysis`
- Current toggles:
  - Analyze AIMS MD output
  - Trajectory analysis

## Inputs

- Uploaded AIMS MD output files
- Uploaded zipped trajectory directories for trajectory analysis
- User-provided atom labels, cutoffs, ranges, and analysis-specific settings

## Outputs

- Plotly charts for MD time series and analysis results
- Tables for RDF, ADP, distortion, and distance results
- Downloadable processed outputs and generated structure files

## How To Use It

1. Enable one of the dynamics-analysis toggles.
2. Upload the required MD outputs or zipped trajectory directory.
3. Choose the analysis mode and configure its options.
4. Run the workflow and inspect plots or tables.
5. Download generated data if needed.

## Key capabilities covered here

- AIMS MD status extraction and visualization
- Hydrogen-bond analysis
- Pair distance analysis
- RDF analysis
- Average-structure generation
- Distortion and ADP analysis on trajectories

## Known Limitations

- MD workflows depend on optional MDAnalysis-related packages.
- Some analysis paths assume specific file naming and output conventions from AIMS runs.
- The legacy Perl helper remains part of the MD preprocessing flow.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- MD logic:
  `src/hpame/domain/md_analysis.py`
- External helper:
  `create_geometry_zip.pl`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
  `src/hpame/domain/md_analysis.py`
