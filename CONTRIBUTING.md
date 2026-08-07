# Contributing

Thank you for improving Hybrid Perovskite Studio. Bug reports, documentation fixes, reference datasets, and focused code contributions are welcome.

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[full,dev,docs]"
```

Run the local release checks before opening a pull request:

```bash
PYTHON=.venv/bin/python scripts/check_release.sh
```

## Contribution expectations

- Keep scientific calculations separate from Streamlit rendering code.
- Add tests for new parsers, transformations, and numerical behavior.
- Include units and coordinate-system conventions in user-visible results.
- Use small redistributable fixtures and document their origin.
- Update the relevant workspace guide and `docs/changelog.md` for user-visible changes.
- Do not commit uploaded research data, secrets, or generated runtime artifacts.

For substantial features, open an issue first so the workflow, expected inputs, and validation approach can be agreed before implementation.
