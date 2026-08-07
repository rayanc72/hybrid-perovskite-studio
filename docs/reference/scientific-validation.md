# Scientific fixture validation report

This report records the values extracted from the maintainer-supplied example data and
the compact regression fixtures derived from it. Please review the attribution and
reference values before the fixtures are treated as release-approved scientific data.

## Source attribution

- Structure, band structure, PDOS, and spin texture: R. Chakraborty et al.,
  “Design of Two-Dimensional Hybrid Perovskites with Giant Spin Splitting and
  Persistent Spin Textures,” *J. Am. Chem. Soc.* **146** (2024), 34811–34821,
  [doi:10.1021/jacs.4c13597](https://doi.org/10.1021/jacs.4c13597).
- Molecular dynamics: R. Chakraborty et al., “Hidden spin-valley locking stabilizes
  nanosecond spin polarization in 2D perovskites,” *Nature Nanotechnology* (2026),
  [doi:10.1038/s41565-026-02238-6](https://doi.org/10.1038/s41565-026-02238-6).

## Values observed in the original files

### Structure

| Quantity | Result |
| --- | --- |
| Formula | `C32H88I24N8Pb4` |
| Atoms | 156 |
| Detected molecular groups | 10 |
| Space group | `Aea2` (No. 41) |
| Lattice lengths represented by the orthogonal vectors | 28.5598, 9.03496, 8.8604 Å |

### Electronic data

| Quantity | Result |
| --- | --- |
| Full PDOS rows | 8,000 |
| PDOS energy range | −15.59664786 to 34.40335214 eV |
| Full-grid total-DOS maximum | 120.95617549 at −6.88305866 eV |
| Total DOS nearest the Fermi level | 1.09043039 |
| `band1001.out` gap | 1.37794 eV |
| `band1002.out` gap | 1.53579 eV |
| `band1003.out` gap | 1.53065 eV |
| Spin-texture rows | 29,560 |
| Spin-texture state range | 1921–1960 (40 states) |
| Spin-texture energy range | −1.99995 to 1.99909 eV |
| Maximum spin-vector norm | 0.99470032 |

The three original band-edge pairs were states 1936/1937. The compact fixture retains
original states 1934–1939, which are renumbered 1–6 by the standalone parser; its
band-edge pair is therefore 3/4 while the energies and gaps remain unchanged.

### Molecular dynamics

| Quantity | Result |
| --- | --- |
| Original archive frames | 10,827 |
| First frame | `geometry-000001.in` |
| Last frame | `geometry-010827.in` |
| Compact fixture frames | 101 consecutive middle frames (`005364`–`005464`) |
| Atoms per compact frame | 62 |
| Formula | `C12H32I8N4O4Pb2` |
| Cell volume | 846.61181648 Å³ |
| Maintainer-confirmed timestep | 0.5 fs |
| Represented duration | 50 fs (0.05 ps) |

## Compact-fixture checks

The automated fixture suite checks:

- structure formula, atom and molecular-group counts, lattice vectors, and space group;
- sampled PDOS dimensions, energy bounds, sampled maximum, and near-Fermi value;
- all three band-segment gaps and energy bounds;
- spin states, row count, energy bounds, and maximum spin norm;
- MD archive safety, ordering, atom consistency, cell volume, and first/last centers of mass.

Exact machine-readable values are in
`src/hps/examples/data/expected_results.json`. Detailed derivation and original
checksums are in `src/hps/examples/data/PROVENANCE.md`.

## Maintainer approval

The project maintainer confirmed on August 6, 2026 that:

1. `MC3I_PbI_100K.in` should use the JACS citation above;
2. the compact derived fixtures may be redistributed under the repository license;
3. the reported space group and three band gaps are appropriate release regression
   references; and
4. the MD regression fixture should use a 0.5 fs timestep and span at least 50 fs.
