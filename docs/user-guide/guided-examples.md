# Guided examples

HPS ships three self-contained examples built from the public scientific regression
data. Each project records its citation, license, intended workflow, file roles, counts,
and aggregate SHA-256 checksums.

## Build a project bundle

List the installed projects:

```bash
hps-examples list
```

Build one or more ZIP bundles:

```bash
hps-examples build structure
hps-examples build electronic
hps-examples build dynamics
```

Use `--output PATH` to choose the resulting filename. Every bundle contains:

- `project.json`, the machine-readable guide and provenance manifest;
- `PROVENANCE.md`, including the complete publication citations and source checksums;
- `expected_results.json`, containing the release regression references;
- the checksum-validated input files under `data/`.

## Structure example

Open the Structure workspace and upload `MC3I_PbI_100K.in`. The overview should report
156 atoms and formula `C32H88I24N8Pb4`; the symmetry reference is `Aea2` (No. 41).

## Electronic example

The Electronic bundle contains three band segments, six PDOS files, and the compact
spin-texture dataset. Follow the `guide` entries in `project.json` for upload grouping
and compare the parsed results with `expected_results.json`.

## Dynamics example

The Dynamics bundle contains the centered 101-frame trajectory slice. Zip the
`data/md/frames` directory, open Dynamics → Trajectory analysis, set the timestep to
0.5 fs, and upload it. HPS should report a 0.05 ps duration and provide metrics CSV plus
first/last structure downloads.
