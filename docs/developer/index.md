# Developer guide

User-facing workflows start in [Getting started](../user-guide/getting-started.md).
This section covers source development, architecture, maintenance, and publication.

## Clone and install

```bash
git clone https://github.com/rayanc72/hybrid-perovskite-studio.git
cd hybrid-perovskite-studio
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[full,dev,docs]"
```

On Windows use `py -3.11 -m venv .venv` and `.venv\Scripts\Activate.ps1` instead.
Run `hps` for the application, or `hps-backend --host 127.0.0.1 --port 8765` for an
explicit backend process. The standard launcher attempts to start a local backend.

## Documentation development

```bash
python scripts/build_doc_examples.py
python -m mkdocs serve
```

The first command validates packaged scientific inputs and generates the downloadable
bundles under the ignored `docs/downloads/` directory. To verify before publishing:

```bash
python -m pytest tests/test_examples.py -q
python -m mkdocs build --strict
```

GitHub Actions publishes the strict build from `main` to
[GitHub Pages](https://rayanc72.github.io/hybrid-perovskite-studio/). The workflow uses
an artifact deployment, so the repository needs only its `main` branch. Pages must be
configured with **GitHub Actions** as its publishing source.

The site follows public `main` and identifies its application baseline. The tagged
[v0.3.0 documentation sources](https://github.com/rayanc72/hybrid-perovskite-studio/tree/v0.3.0/docs)
remain available for historical reference; published tags and assets are immutable.

## Maintainer references

- [Architecture](../architecture.md)
- [Backend modernization](../reference/backend-modernization.md)
- [Implementation map](implementation-map.md)
- [Documentation workflow](../reference/documentation-workflow.md)
- [Release acceptance](../reference/release-acceptance.md)
- [Contributing](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/CONTRIBUTING.md)
- [Public release procedure](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/RELEASING.md)
