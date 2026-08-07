# Scientific regression fixture provenance

These fixtures were supplied by the project maintainer and curated for deterministic,
redistributable Hybrid Perovskite Studio regression tests. They are distributed under
the repository license. The numerical results are regression references, not new
scientific claims.

## Structure, band structure, PDOS, and spin texture

R. Chakraborty, P. C. Sercel, X. Qin, D. B. Mitzi, and V. Blum,
“Design of Two-Dimensional Hybrid Perovskites with Giant Spin Splitting and
Persistent Spin Textures,” *J. Am. Chem. Soc.* **146** (2024), 34811–34821.
https://doi.org/10.1021/jacs.4c13597

The structure is retained in full. The PDOS grid contains the first and last data
points plus every 80th original point. Each band segment retains all 81 k-points and
the six states surrounding the original band edge (original states 1934–1939). The
spin fixture retains complete data for original states 1929 and 1930.

## Molecular dynamics

R. Chakraborty et al., “Hidden spin-valley locking stabilizes nanosecond spin
polarization in 2D perovskites,” *Nature Nanotechnology* (2026).
https://doi.org/10.1038/s41565-026-02238-6

The MD fixture contains 101 consecutive frames from the middle of the supplied
10,827-frame archive: `geometry-005364.in` through `geometry-005464.in`, centered on
`geometry-005414.in`. At the maintainer-confirmed 0.5 fs timestep, this represents
50 fs. Velocities, lattice vectors, atomic ordering, and coordinates are unchanged.
Tests construct the ZIP archive in memory so a binary archive does not need to be
stored in Git.

## Original-file checksums

- Structure: `5b3ea174eb4b62c949c74eebfc91490a65bf1895a1d431ce533d731701881b4b`
- Band 1001: `9a99db661287b25c3df70eacf48698e887577bb2332a3701aeef04b1e235c6f5`
- Band 1002: `e1fba9f05d42588dcf0aedc1902d332ccec1f7a665f1e04343e7e4306b08d6d5`
- Band 1003: `caef067f7320ddb67884df81009d6cf2cfaa1806f76b61868f238ff293293bfe`
- Total DOS: `9715945b1c7167f8e4fd7fc44a78509c27b8e4cd8e2ce0de16ce5ef66f669691`
- Spin texture: `20d6da314e7cc4e4ae0556338468b4f6ba80d5f7e0aa8f1913accfd846389d93`
- MD archive: `a0deb3024eeeb6bf3fdade174e9026b4ae1846d46000ad277c1fbcd2ad485161`
