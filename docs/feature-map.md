# Feature Map

## Workspaces

- Structure
  - Overview
    - Upload structure
    - Review loaded structure
    - Remove current structure
  - Analysis
    - Symmetry
      - Symmetrize structure
      - Anisotropic displacement parameters
      - Calculate polarization direction
    - Molecules
      - Find center of mass
      - Calculate dipole moment
      - Charge analysis
    - Structure Metrics
      - Calculate interatomic distances
      - Calculate octahedral distortions
      - Calculate percentage deviation (between two structures)
    - Pair Distribution Function Analysis
      - Simulate PDF
      - Plot RDF
      - Compare experimental PDF
      - Convert reduced PDF to g(r)
  - Transformations
    - Molecule Operations
      - Rotation
        - Rotate Individual Molecules
        - Rotate Multiple Molecules
        - Random Rotation
        - Interpolate by Rotation
        - Rotate Part of Molecules
        - Rotate by Dipole Moment
      - Reflection
      - Translation
        - Molecules
        - Atoms
      - Deletion
      - Labelling
        - Select one or more molecule groups
        - Assign an individual label suffix to each selected molecule
        - Export a custom-labelled `geometry.in` with only those atoms relabelled
    - Lattice Operations
      - Translation
        - Molecules
        - Atoms
      - Interpolation

- Electronic
  - Bands and Spin
    - Plot bandstructure
    - Plot spin texture
    - Plot partial density of states (PDOS)
  - Advanced
    - Plot polarization
    - Plot absorption spectra

- Dynamics
  - Analyze AIMS MD output
    - Plot parsed MD output
    - Generate geometry files
  - Trajectory analysis
    - H-Bond Analysis
    - Distance Analysis
    - Average Structure
    - Distortion Analysis
    - Pair Distribution Function
    - Anisotropic Displacement Parameter

- Utilities
  - Run your own script
    - JupyterLite browser workspace
  - Plot Data
    - Custom dataset plotting

## Source Of Truth

The live navigation tree is defined in [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py).
