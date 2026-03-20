# Getting Started

## Overview

Hybrid Perovskite Studio is a Streamlit app for hybrid perovskite structure analysis, transformations, electronic-property workflows, molecular-dynamics analysis, and several experimental utilities.

## Run the app

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
streamlit run src/hpame/app.py
```

## Initial workflow

1. Start the app.
2. Upload a structure file in `aims geometry`, `CIF`, or `.next_step` format.
3. Use the sidebar to enable one feature area at a time.
4. Inspect plots, tables, and download buttons produced by each tool.

## Main feature areas

- Structure Analysis
- Structure Transformations
- Electronic Analysis
- Dynamics Analysis
- Experimental

## Runtime notes

- Local secrets belong in `.streamlit/secrets.toml`.
- Runtime-generated artifacts should live under `tmp/` or `output/`.
- Archived compatibility shims live under `legacy_shims/` and are not the primary runtime path.
