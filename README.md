# Hybrid Perovskite Studio

Hybrid perovskites are a highly tunable family of functional materials with broad relevance across materials science, chemistry, and condensed-matter physics. Their hybrid organic-inorganic character makes them especially valuable for studying structure-property relationships through systematic changes in composition, molecular orientation, and lattice geometry. At the same time, that same hybrid character makes them difficult to analyze with many conventional structure-chemistry workflows, since the organic and inorganic sublattices often need to be treated differently.

Hybrid Perovskite Studio (HPS) is a workspace-oriented environment, built upon Streamlit, designed to support this kind of analysis and modelling. Its Structure Workspace focuses on tools for parsing, analyzing, and transforming hybrid perovskite structures while explicitly distinguishing between molecular and inorganic building blocks. Starting from experimental or simulated structures, users can inspect symmetry, molecular connectivity, bond lengths, bond angles, distortion metrics, anisotropic displacement information, pair distribution functions, and polarization-related quantities. The same workspace also supports structure editing and modelling operations, including molecule-specific rotations, reflections, translations, deletions, and interpolation-based transformations.

Beyond structure chemistry, HPS also provides tools for analyzing computational outputs. The Electronic Workspace is currently tailored especially to FHI-aims-style inputs and outputs, and includes functionality for plotting band structures, spin textures, partial densities of states, polarization-related quantities, absorption spectra, and Brillouin-zone information. The Dynamics Workspace extends the analysis to time-dependent simulation data, with tools for extracting trajectory-based structural metrics and monitoring how distortions and related descriptors evolve over time. A Utilities Workspace collects supporting tools for plotting and lightweight custom scripting.

HPS is an active research software project and is still evolving. It grew out of a longer collection of notebook-based and script-based workflows developed for hybrid-perovskite research, and is gradually being consolidated into a more structured, reusable application. Although it focuses upon hybrid perovskites, the tools are equally applicable to other materials classes. While the codebase is already useful for day-to-day analysis, some workflows remain under active refinement and edge cases may still appear. The broader goal is to continue expanding HPS into a flexible and maintainable platform for hybrid perovskite modelling, analysis, and visualization.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
streamlit run src/hps/app.py
```

## Docs

- [Getting Started](docs/user-guide/getting-started.md)
- [Feature Map](docs/feature-map.md)
- [Workspace Guides](docs/index.md)
- [Screenshots Guide](docs/user-guide/screenshots.md)

## Gallery

![Landing Page](docs/images/screenshots/landing-page.png)

![Structure Workspace](docs/images/screenshots/structure-workspace.png)

![Band Structure Studio](docs/images/screenshots/band-structure-studio.png)

![Dynamics Workspace](docs/images/screenshots/dynamics-workspace.png)

## Notes

- Main entrypoint: `streamlit run src/hps/app.py`
- Runtime files belong under `tmp/` and `output/`
- Navigation is defined in `src/hps/ui/navigation.py`
