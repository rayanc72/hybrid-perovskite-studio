# Getting Started

## Overview

Hybrid Perovskite Studio is a Streamlit app for hybrid perovskite structure analysis, structure transformation, electronic-output visualization, molecular-dynamics workflows, and utility-style plotting or scripting tools.

## Install and run the app

Version 0.3.0 is available on GitHub; PyPI currently provides 0.2.1.
Install this release from its GitHub tag (requires Git):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "hybrid-perovskite-studio[full] @ git+https://github.com/rayanc72/hybrid-perovskite-studio.git@v0.3.0"
hps
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
streamlit run src/hps/app.py
```

## First-Time Workflow

1. Start the app.
2. On the landing page, choose a workspace from the four options below the hero.
3. If you are working with structures, open `Structure`.
4. Use the upload box at the top of the Structure workspace to load a file in `.in`, `.cif`, or `.next_step` format.
5. Use the `Current Structure` summary to inspect the loaded structure and export geometry files.
6. Choose `Analysis` or `Transformations` as needed. The upload box and summary remain above the view controls.

## Workspaces

- `Structure`: upload, inspect, analyze, transform, and export structures
- `Electronic`: plot polarization, DOS, bandstructure, spin texture, and absorption outputs
- `Dynamics`: process MD outputs and perform trajectory analysis
- `Utilities`: open JupyterLite or use generic plotting/data helpers

## Navigation Notes

- The app starts on a minimal landing page instead of opening directly into a workflow.
- The `Explore every tool` link opens the full registry-driven feature map.
- The visible workspace selectors and feature map are generated from a shared registry in [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py).

## Runtime notes

- Local secrets belong in `.streamlit/secrets.toml`.
- Runtime-generated artifacts should live under `tmp/` or `output/`.
