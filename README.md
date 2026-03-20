# Hybrid Perovskite Studio

Hybrid Perovskite Studio is a Streamlit application for hybrid perovskite analysis, structure manipulation, and simulation-output visualization. This repository now exposes a packaged entrypoint and dependency model so the app can be installed and run more reproducibly.

## Run the packaged app

Create a virtual environment, then install the full app stack:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
streamlit run src/hpame/app.py
```

If Streamlit reruns crash with module-watcher issues in your local environment, keep the repo-local config in `.streamlit/config.toml` and restart the server.

The packaged launcher checks whether the legacy app dependencies are available. If they are, it executes the full legacy Streamlit UI. If they are not, it shows a bootstrap screen with the missing dependency groups and install hints.

## Dependency groups

- `core`: general scientific and file-processing libraries used across the app
- `md`: MDAnalysis-based trajectory workflows
- `pdf`: diffpy-backed pair-distribution-function workflows
- `viz`: optional plotting/widget integrations
- `auth`: Streamlit authenticator support
- `full`: current end-to-end legacy app dependency set
- `dev`: test and lint tooling

Compatibility install:

```bash
pip install -r requirements.txt
```

Local secrets should go in `.streamlit/secrets.toml`. A safe template is provided in `.streamlit/secrets.example.toml`.

## Package layout

```text
src/hpame/
  app.py            Packaged Streamlit entrypoint
  domain/           Narrow wrappers around structure, PDF, MD, and electronic logic
  io/               Shared path/runtime directory helpers
  legacy/           Compatibility loader for the flat-file app
  services/         Dependency and runtime coordination
  ui/               Bootstrap page and sidebar catalog
```

The current scientific implementation is being migrated into the package incrementally. The old compatibility shims now live under `legacy_shims/`; the packaged entrypoint and packaged PDF module are the primary runtime path.

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Linting:

```bash
ruff check src tests
```

## Notes

- Preferred entrypoint: `streamlit run src/hpame/app.py`
- Legacy compatibility shims live under `legacy_shims/`
- Runtime output directories are standardized under `output/` and `tmp/`
- See [docs/architecture.md](docs/architecture.md) for the package boundaries and migration model
