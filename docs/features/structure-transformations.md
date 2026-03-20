# Structure Transformations

## What It Does

The Structure Transformations section modifies the uploaded structure through geometric operations. It includes rotations, reflections, translations, deletions, and interpolation workflows.

## Where It Appears in the UI

- Sidebar section:
  `Structure Transformations`
- Current toggles:
  - Rotation
  - Reflection
  - Translation
  - Deletion
  - Standard interpolation

## Inputs

- An uploaded structure is required.
- Some workflows require molecule selections, axis definitions, Miller indices, angles, or uploaded start/end structures.

## Outputs

- Modified structure objects in the active app session
- Downloadable `geometry.in` and labelled structure files
- ZIP archives for generated structure series
- Optional structure visualizations for selected operations

## How To Use It

1. Upload a structure file.
2. Enable one transformation tool in the sidebar.
3. Provide the required molecule indices, axes, planes, or interpolation inputs.
4. Apply the transformation.
5. Download the resulting structure files or generated ZIP archive.

## Key capabilities covered here

- Individual and batch molecule rotations
- Random symmetric and asymmetric rotations
- Partial molecule rotations
- Plane-based alignment and reflections
- Translational operations
- Molecule deletion
- Standard interpolation between structures

## Known Limitations

- Several transformation flows are large and highly interactive, so they rely on current UI state rather than small isolated service objects.
- Interpolation and structure-series generation may create multiple downloadable outputs with limited workflow summarization.
- Optional visualization blocks can be heavier than the basic file-export paths.

## Code Touchpoints

- UI:
  `src/hpame/ui/app_main.py`
- Transformation logic:
  `src/hpame/domain/structure_manager.py`
- Molecule helpers:
  `src/hpame/domain/molecule_builder.py`

## Last Verified Against Code

- Date:
  2026-03-19
- Files reviewed:
  `src/hpame/ui/app_main.py`
  `src/hpame/domain/structure_manager.py`
