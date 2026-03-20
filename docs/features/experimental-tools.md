# Experimental and Utility Tools

## What It Does

This section groups the app’s utility-style tools that do not fit cleanly into the core structure, electronic, or dynamics categories. Based on the current code, this includes user-script execution hooks, dataset math-expression tools, and generic plotting utilities.

## Where It Appears in the UI

- Sidebar section:
  `Experimental`
- Current toggles:
  - Run your own script
  - Plot Data

The broader app code also includes utility-style subsections such as:

- Dataset modification via math expressions
- Generic plot generator tools

## Inputs

- Uploaded generic data files
- User-defined plot configuration
- User-defined math expressions for dataset modification

## Outputs

- Updated data tables
- Generated plots
- Downloadable image files and transformed datasets

## How To Use It

1. Enable the relevant experimental or utility toggle.
2. Upload the target data file(s).
3. Configure labels, axes, math expressions, or plot settings.
4. Generate the output.
5. Download the resulting figure or transformed data if needed.

## Known Limitations

- These workflows are broad utility surfaces and may be less constrained than the domain-specific tools.
- Some utility subsections still live in the main UI module without dedicated domain-level abstraction.
- The exact behavior of “Run your own script” should be reviewed carefully before exposing it broadly in external-facing docs.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- Shared helpers:
  `src/hpame/domain/electronic_property.py`
  `src/hpame/domain/structure_manager.py`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
