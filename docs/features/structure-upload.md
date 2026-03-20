# Structure Upload and Initialization

## What It Does

This workflow initializes the app from an uploaded structure file. It reads the uploaded structure, detects molecular groupings, labels atoms, and makes the structure available to the rest of the analysis and transformation tools.

## Where It Appears in the UI

- Main page section:
  `Upload a structure file (aims geometry or CIF) to get started`
- The uploader appears before the sidebar-driven feature workflows.

## Inputs

- Required:
  one uploaded structure file
- Supported file types:
  `.in`, `.cif`, `.next_step`
- Current default bonding exception:
  `("F", "I")`

## Outputs

- Parsed structure in memory for the active rerun
- Detected molecule groups
- Optional details view with:
  - labelled-atom download
  - symmetry information
  - detected molecules list
  - geometry download
  - optional 3D structure viewer

## How To Use It

1. Launch the app.
2. Upload a supported structure file.
3. Wait for the success message confirming atom and molecule counts.
4. Expand `Show structure details and downloads` if you need the optional detail sections.
5. Enable `Load 3D structure viewer` only if you want the interactive structure view.

## Known Limitations

- The app currently reparses the uploaded file on reruns instead of storing the full parsed structure in `st.session_state`.
- The 3D structure viewer is opt-in and kept off by default in the current debug-hardened flow.
- Bonding customization UI exists only as commented-out code at the moment.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- Parsing and initialization:
  `src/hpame/domain/structure_manager.py`
- Narrow wrappers:
  `src/hpame/domain/structure/parsing.py`
  `src/hpame/domain/structure/analysis.py`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
  `src/hpame/domain/structure_manager.py`
