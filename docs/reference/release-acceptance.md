# Release acceptance checklist

Use this checklist for every public release candidate. Record the candidate commit and
date in the release issue or notes rather than editing historical results into this
template.

## Automated gate

Run from a clean checkout with Python 3.11:

```bash
python -m venv .venv
.venv/bin/pip install -e ".[full,dev,docs]"
PYTHON=.venv/bin/python scripts/check_release.sh
```

The gate must pass all of the following:

- import, syntax, statement-style, and correctness lint checks for maintained package layers;
- undefined-name lint checks for the full test suite;
- unit, API, scientific-regression, cache-performance, and Streamlit smoke tests;
- a strict MkDocs build;
- isolated source-distribution and wheel builds.

## Manual application smoke check

- [ ] Launch `hps` from the built wheel in a fresh environment.
- [ ] Confirm no backend-readiness warning appears and `/health` reports the same version.
- [ ] Open Structure, Electronic, Dynamics, and Utilities from the start page.
- [ ] Upload the maintained structure fixture and confirm formula and space group.
- [ ] Load the PDOS, band, and spin fixtures and compare against the validation report.
- [ ] Load the trajectory fixture at 0.5 fs and confirm 101 frames and 0.05 ps duration.
- [ ] Download trajectory metrics plus first and last structure artifacts.
- [ ] Confirm invalid or oversized uploads produce actionable errors.

## Distribution and documentation

- [ ] Confirm the version matches in package metadata, backend health, tag, and release notes.
- [ ] Inspect wheel and source archive contents; no secrets, caches, or private data are present.
- [ ] Confirm scientific fixture provenance and citations are visible in the documentation.
- [ ] Check README installation commands from a fresh environment.
- [ ] Verify the public documentation site and repository links.
- [ ] Review the changelog, known limitations, license, citation, security, and contribution files.

The maintained release limitations are documented in
[Known limitations](known-limitations.md). Release notes must distinguish these accepted
constraints from regressions that block publication.

## Publication

- [ ] Confirm CI is green on the exact candidate commit.
- [ ] Create and verify the annotated release tag.
- [ ] Publish artifacts only from the tagged commit.
- [ ] Perform one clean installation from the published artifacts.
- [ ] Record any deferred issues with owners and target milestones.
