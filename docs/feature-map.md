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
      - PDF analysis
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

The live navigation tree is defined in [src/hps/ui/navigation.py](../src/hps/ui/navigation.py). 
