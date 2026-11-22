# Workspace implementation map

Source pointers for maintainers. User workflows belong in the workspace guides and tutorials.

## Structure Workspace

- UI and routing:
  [src/hps/ui/app_main.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/app_main.py)
- Structure overview renderer:
  [src/hps/ui/workspaces/structure/overview.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/overview.py)
- Structure workspace state:
  [src/hps/ui/workspaces/structure/state.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/state.py)
- Structure workspace navigation:
  [src/hps/ui/workspaces/structure/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/navigation.py)
- Symmetry renderer:
  [src/hps/ui/workspaces/structure/analysis/symmetry.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/symmetry.py)
- PXRD renderer and plotting helpers:
  [src/hps/ui/workspaces/structure/analysis/pxrd.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/pxrd.py)
- PDF renderer and reduced-PDF parser:
  [src/hps/ui/workspaces/structure/analysis/pdf.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/pdf.py)
- Charge-analysis parsers:
  [src/hps/ui/workspaces/structure/analysis/charge.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/charge.py)
- Molecule-analysis renderer:
  [src/hps/ui/workspaces/structure/analysis/molecules.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/molecules.py)
- Structure metric renderers and lattice-deviation helpers:
  [src/hps/ui/workspaces/structure/analysis/metrics.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/analysis/metrics.py)
- Rotation workflows:
  [src/hps/ui/workspaces/structure/transformations/rotation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/transformations/rotation.py)
- Reflection, translation, deletion, labelling, and interpolation workflows:
  [src/hps/ui/workspaces/structure/transformations/operations.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/structure/transformations/operations.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/navigation.py)
- Structure logic:
  [src/hps/domain/structure_manager.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/structure_manager.py)
- Molecule helpers:
  [src/hps/domain/molecule_builder.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/molecule_builder.py)
- PXRD logic:
  [src/hps/domain/structure_manager.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/structure_manager.py)
- PDF logic:
  [src/hps/domain/pdf_analysis.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/pdf_analysis.py)


## Electronic Workspace

- Workspace UI:
  [src/hps/ui/workspaces/electronic.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/electronic.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/navigation.py)
- Electronic logic:
  [src/hps/domain/electronic_property.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/electronic_property.py)
- Tool helpers:
  [src/hps/tools/plot_band.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/tools/plot_band.py)
  [src/hps/tools/scan_cbm.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/tools/scan_cbm.py)


## Band Structure Studio implementation

- Bandstructure plotting uses Matplotlib.
- Brillouin-zone plotting uses Plotly.
- The workspace UI lives in:
  - [src/hps/ui/workspaces/electronic.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/electronic.py)
- Domain and plotting helpers live in:
  - [src/hps/domain/electronic_property.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/electronic_property.py)


## Dynamics Workspace

- Workspace UI:
  [src/hps/ui/workspaces/dynamics.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/dynamics.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/navigation.py)
- MD logic:
  [src/hps/domain/md_analysis.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/domain/md_analysis.py)

## Utilities Workspace

- Workspace UI:
  [src/hps/ui/workspaces/utilities.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/workspaces/utilities.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/v0.3.0/src/hps/ui/navigation.py)
