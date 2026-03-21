# Getting Started

## Overview

Hybrid Perovskite Studio is a Streamlit app for hybrid perovskite structure analysis, structure transformation, electronic-output visualization, molecular-dynamics workflows, and utility-style plotting or scripting tools.

## Run the app

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
streamlit run src/hps/app.py
```

If you need the PDF-analysis workflow, install the PDF extra separately:

```bash
pip install -e ".[pdf]"
```

On macOS, the PDF extra may also require:

```bash
brew install gsl
```

## First-Time Workflow

1. Start the app.
2. On the landing page, choose a workspace from the top card row.
3. If you are working with structures, open `Structure`.
4. In `Structure -> Overview`, upload a structure file in `.in`, `.cif`, or `.next_step` format.
5. Use the `Current Structure` card to inspect summary information and export geometry files.
6. Move into `Analysis` or `Transformations` as needed.

## Workspaces

- `Structure`: upload, inspect, analyze, transform, and export structures
- `Electronic`: plot polarization, DOS, bandstructure, spin texture, and absorption outputs
- `Dynamics`: process MD outputs and perform trajectory analysis
- `Utilities`: open JupyterLite or use generic plotting/data helpers

## Navigation Notes

- The app starts on a minimal landing page instead of opening directly into a workflow.
- The `Browse feature map` expander shows the full tool tree when needed.
- The visible workspace selectors and feature map are generated from a shared registry in [src/hps/ui/navigation.py](../../src/hps/ui/navigation.py).

## Runtime notes

- Local secrets belong in `.streamlit/secrets.toml`.
- Runtime-generated artifacts should live under `tmp/` or `output/`.
