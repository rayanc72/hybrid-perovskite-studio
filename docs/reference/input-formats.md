# Input formats and scientific conventions

This reference describes the GitHub v0.3.0 workflows. Import acceptance alone does not
establish scientific validity; check the assumptions for the selected analysis.

## Structures and bonded groups

| Input | Requirement | Convention |
| --- | --- | --- |
| Structure workspace | `.in`, `.next_step` (FHI-aims) or `.cif` | Cartesian geometry is represented in Å; periodicity and lattice come from the structure |
| Rotation direction | Three integers `h k l`, e.g. `0 0 1` | Linear combination of direct lattice vectors, not necessarily a Cartesian axis |
| Rotation angle | Number in degrees | Applies to selected finite groups |
| Experimental PXRD | Two-column `.csv`, `.txt`, `.xy`, `.dat`, or `.chi` | Match the selected `2theta` or `q` x-axis; broadening remains in degrees of `2theta` |
| PDF comparison | Experimental `.gr` input | Verify the data convention and distance units for the chosen PDF workflow |

Bonded groups are determined geometrically, not by chemical identity or bond order.
The detector compares distances with ASE covalent radii plus per-atom tolerances:
0.1 Å for C/H/N/O/S, 0.5 Å for Cl, and 0.25 Å plus configured bond padding for other
elements. It respects periodic axes. Non-closing image translations identify periodic
networks; finite groups can be reconstructed across cell boundaries.

The total group count includes finite molecules, isolated atoms, and periodic
networks. Only finite groups can be used by finite-molecule rotation, reflection,
center-of-mass, and dipole operations. Original group numbering is retained.
See [Structure limitations](../features/structure-workspace.md#notes-and-limitations).

## Electronic data

| Workflow | Required input | Optional input / interpretation |
| --- | --- | --- |
| Band plot and Excel | `band####.out` or `band####.out.no_soc` | Matching `geometry.in` gives reciprocal-space distances; `control.in` gives path labels |
| Brillouin zone | `geometry.in` from that calculation | `control.in` overlays the path |
| PDOS | FHI-aims DOS/element-projected `.dat` files | Upload total and element files together; filenames identify roles |
| Spin texture | FHI-aims `spin_texture.dat` | Related AIMS `.out`; 3D workflow also accepts geometry and preset JSON |

### Band columns and alignment

A numeric band row contains a k-point index, three fractional k coordinates, then
alternating occupation/energy pairs. Energies are in eV. Keep filenames unchanged;
no-SOC files are accepted directly. A standard `.out` filename does not prove SOC.

Each dataset is shifted by its own detected VBM. This is useful for band-shape
comparison but does not provide an absolute energy reference between calculations.
With geometry, Cartesian k components and distances use Å⁻¹; without it, distances
use fractional-coordinate units. Excel records the distinction in `momentum_units`.
The workbook matches exact fractional k coordinates and does not interpolate grids.
See [Band Structure Studio](../features/band-structure-studio.md) for all columns.

### PDOS and spin examples

The [Electronic bundle](../downloads/hps-example-electronic.zip) supplies small,
valid files rather than schematic headers. `data/pdos/KS_DOS_total.dat` and the five
`*_l_proj_dos.dat` files demonstrate FHI-aims energy and orbital-column conventions.
The total DOS reader uses column 1 for energy and column 2 for DOS. In projected
files the common layout is energy, total projection, then s, p, d, and f projections
when present. Pb/Sn s/p plotting requires at least four numeric columns.
Do not rename arbitrary two-column data to these filenames. Check the calculation's
energy reference and projection definitions before comparing magnitudes or shifting axes.

`data/spin/spin_texture.dat` demonstrates the expected k-point, state, energy, and
spin-component records. The compact fixture retains only states **1929 and 1930**;
select a retained state rather than an absent full-calculation state. The parser
accepts 9 or 12 numeric columns: `k_point kx ky kz state eigenvalue sigma_x sigma_y
sigma_z`, optionally followed by `rel_kx rel_ky rel_kz`. The example header reports
k in Å⁻¹ and energies in eV; spin components retain the source convention. It is sampled
and should not be treated as the full spin grid. See
[fixture validation](scientific-validation.md) for source versus sampled values.

## Trajectory archives

Use a ZIP of **`geometry*.in`** FHI-aims files for the full interactive trajectory
analysis. Keep consistent atom identity, order, and count across frames. Use
zero-padded filenames, for example:

```text
frames/
  geometry-000001.in
  geometry-000002.in
  geometry-000003.in
```

Paths are sorted lexically. A single structure file is treated as one frame; a
multi-frame file is not a substitute for the expected one-file-per-frame layout.
The backend inventory accepts `.in`, `.cif`, `.xyz`, and `.pdb`, but downstream
MDAnalysis construction searches specifically for `geometry*.in`. A successful
inventory of another format does not guarantee interactive analysis support.

Enter the saved-frame interval in **fs**, positive and no greater than the UI limit
of **50 fs**. Backend metrics assign frame zero time zero and calculate
`time_ps = frame_index * timestep_fs / 1000` and duration
`(frame_count - 1) * timestep_fs / 1000`. Cartesian positions are in Å and cell
volumes in Å³. Analysis-specific cutoffs and units must be checked in the selected tool.

Default extraction limits are **10,000 archive entries**, **250,000,000 bytes per
file**, and **1,000,000,000 bytes total expanded contents**. Streamlit's upload-size
setting can impose a smaller compressed-file limit. Unsafe paths and links are
rejected. Do not include duplicate frame trees or an additional nested archive.

The current downstream MDAnalysis builder loads coordinate frames after the first
file into its trajectory. Interactive analyses can therefore contain one fewer frame
than the backend inventory, and their time origin must not be assumed identical to
the metrics CSV. Check this boundary before time-sensitive interpretation; the
101-frame / 0.05 ps reference describes the backend inventory.

For direct MD-output parsing, select **Analyze AIMS MD output** and upload AIMS `.out`
files; that workflow is separate from the frame-archive path.

## General tables and math expressions

In **Utilities → Plot Data**, select parsing options that match the delimiter and
header before choosing x/y columns. The displayed safe-name mapping identifies the
column names accepted in expressions. For example, if the mapping includes `energy`:

```text
energy_shifted = energy - 1.5
energy_squared = energy_shifted ** 2
```

Use one assignment per line. Available functions are `sin`, `cos`, `tan`, `log`,
`sqrt`, `abs`, and `exp`, with constants `pi` and `e`. Trigonometric arguments are in
radians; `log` is the natural logarithm. Operations do not perform unit conversion
or dimensional checking automatically. Check domains before applying `log` or `sqrt`.
Plot exports include PNG/PDF and a reusable JSON plotting configuration.
