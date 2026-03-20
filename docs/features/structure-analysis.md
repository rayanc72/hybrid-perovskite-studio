# Structure Analysis

## What It Does

The Structure Analysis section provides analysis tools for the currently uploaded structure, including symmetry-related utilities, molecule-level geometric analysis, dipole and polarization direction analysis, distances, distortions, ADP extraction, PDF workflows, and charge-related analysis.

## Where It Appears in the UI

- Sidebar section:
  `Structure Analysis`
- Current toggles:
  - Symmetrize structure
  - Find center of mass
  - Calculate dipole moment
  - Calculate polarization direction
  - Calculate atomic distances
  - Calculate octahedral distortions
  - Calculate percentage deviation
  - Anisotropic displacement parameters
  - PDF analysis
  - Charge analysis

## Inputs

- An uploaded structure is required for all tools in this section.
- Some tools require additional uploaded files or atom-symbol inputs.
- PDF-related comparisons can also require experimental `.gr` or related files.

## Outputs

- Tables for per-molecule, per-atom, or per-group metrics
- Plotly and Matplotlib visualizations
- Download buttons for generated data files and plots
- Symmetry information and generated structure exports

## How To Use It

1. Upload a structure file.
2. Enable one Structure Analysis toggle from the sidebar.
3. Fill in any required fields for atom labels, ranges, or uploaded comparison files.
4. Run the calculation or inspect auto-generated outputs.
5. Download any generated data, structures, or plots as needed.

## Key capabilities covered here

- Symmetrized structure generation
- ADP extraction from CIF files
- Dipole moment and polarization direction analysis
- Distance and distortion calculations
- PDF and RDF simulation/comparison tools
- Charge-difference and charge-summary views
- Center-of-mass and related molecule-level summaries

## Known Limitations

- Several tools mix UI code and analysis logic, so behavior can be tightly coupled to current Streamlit layout.
- Some PDF and charge-analysis flows depend on optional scientific libraries and uploaded external files.
- Parts of the larger structure-analysis surface still reflect legacy implementation patterns.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- Structure logic:
  `src/hpame/domain/structure_manager.py`
- PDF logic:
  `src/hpame/domain/pdf_analysis.py`
- Molecule helpers:
  `src/hpame/domain/molecule_builder.py`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
  `src/hpame/domain/structure_manager.py`
  `src/hpame/domain/pdf_analysis.py`
