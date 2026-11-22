# Guided examples

Three examples use redistributable scientific regression data. Each includes a
citation, input roles, file counts, aggregate SHA-256 checksums, and expected results.

## Download a ready-to-use bundle

| Example | Download | Walkthrough |
| --- | --- | --- |
| Structure | [Structure ZIP](../downloads/hps-example-structure.zip) | [Inspect, rotate, and export a CIF](../tutorials/structure.md) |
| Electronic | [Electronic ZIP](../downloads/hps-example-electronic.zip) | [Plot bands and export Excel data](../tutorials/bands.md) |
| Dynamics | [Dynamics ZIP](../downloads/hps-example-dynamics.zip) | [Validate and inspect a trajectory](../tutorials/dynamics.md) |

Extract the bundle before uploading individual inputs. For Dynamics, upload the
included **`trajectory-frames.zip`**, without extracting that inner archive.

Every current documentation download contains:

- `README.md`: numbered instructions and links to the complete tutorial;
- `project.json`: the machine-readable guide and provenance manifest;
- `PROVENANCE.md`: publication citations and source checksums;
- `expected_results.json`: numerical regression references;
- checksum-validated input files under `data/`.

The Dynamics bundle also includes a ready-to-upload `trajectory-frames.zip` containing
only frame files. Do not upload the outer project ZIP: it contains duplicate frame
representations and documentation rather than a single trajectory.

## Build locally

```bash
hps-examples list
hps-examples build structure
hps-examples build electronic
hps-examples build dynamics
```

Use `--output PATH` to choose the resulting filename.

### Bundle versions

The commands use the **installed package**. The immutable v0.3.0 package creates the
original bundles with JSON instructions, provenance, references, and input files.
It does not add `README.md` or the inner trajectory ZIP. Use the documentation
**downloads above** for those additions, or build from current public `main`.
For an original Dynamics bundle, zip only `data/md/frames` before uploading it.

The documented application steps apply to v0.3.0. Example packaging improvements do
not change the scientific input data, its checksums, or the existing release assets.

## Expected results and interpretation

- **Structure:** 156 atoms, `C32H88I24N8Pb4`, space group `Aea2` (No. 41).
- **Electronic:** three compact band segments with six retained states; per-segment
  gaps are recorded in `expected_results.json`. The compact PDOS and spin data are
  sampled fixtures, not the full original datasets.
- **Dynamics:** 101 frames, 62 atoms per frame, 0.5 fs spacing, and 0.05 ps duration.
  This short slice supports workflow checks, not long-time statistical conclusions.

See [Scientific fixture validation](../reference/scientific-validation.md) for original
versus compact dataset values and [About HPS](../about.md#citation-and-data-attribution)
for citation guidance.
