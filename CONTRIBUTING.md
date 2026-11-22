# Contributing

Bug reports, documentation fixes, reference datasets, and focused code contributions
are welcome. Start from the public repository's `main` branch.

## Development setup

```bash
git clone https://github.com/rayanc72/hybrid-perovskite-studio.git
cd hybrid-perovskite-studio
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[full,dev,docs]"
```

Windows PowerShell uses `py -3.11 -m venv .venv` and
`.venv\Scripts\Activate.ps1`. See the [developer guide](docs/developer/index.md)
for application and documentation commands.

For documentation changes, generate the example downloads, run the example tests,
and build the docs in strict mode:

```bash
python scripts/build_doc_examples.py
python -m pytest tests/test_examples.py -q
python -m mkdocs build --strict
```

For application or release changes, run the complete gate on macOS/Linux:

```bash
PYTHON=.venv/bin/python scripts/check_release.sh
```

The Bash script is also usable through an appropriate Bash environment on Windows;
its individual commands are documented in [release acceptance](docs/reference/release-acceptance.md).

## Contribution expectations

- Keep scientific calculations separate from Streamlit rendering code.
- Test new parsers, transformations, and numerical behavior with meaningful examples.
- Include units and coordinate-system conventions in scientific results.
- Use small redistributable fixtures and record their origin.
- Update the matching workspace guide, tutorial, packaged example manifest, and changelog when applicable.
- Do not commit uploaded research data, credentials, private paths, or generated runtime artifacts.

Open a pull request against public `main`; use a focused title, describe the resulting
behavior, and report relevant validation. Temporary contributor branches can be deleted
after merging. For substantial features, discuss inputs and scientific validation in
an issue before implementation. Follow the [documentation workflow](docs/reference/documentation-workflow.md)
and [public release procedure](RELEASING.md) when maintaining those areas.
