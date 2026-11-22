# Public releases

This procedure applies to a fresh clone of the public repository. Its maintained
branch is `main`; no private remote or internal tracking branch is required.

## Prepare a candidate

1. Start from current public `main` and review the exact diff to be published.
   Bring selected changes forward without merging obsolete or private history.
2. Set the application version in `src/hps/__init__.py` when making an application
   release, and update the changelog and dependency metadata as needed.
3. Align workspace guides, tutorials, example manifests, expected results, README,
   and the documentation's version labels.
4. Review the changed files and built distributions for private data, local filesystem
   paths, credentials, caches, and generated research artifacts.
5. Run the [release acceptance checklist](docs/reference/release-acceptance.md) and
   complete the application smoke checks. Record the candidate SHA and results.

From the cloned repository on macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[full,dev,docs]"
PYTHON=.venv/bin/python scripts/check_release.sh
```

Windows environment setup is described in [Contributing](CONTRIBUTING.md). The gate
runs correctness lint, the full test suite, example-download generation, a strict docs
build, and source/wheel builds. CI must pass on the exact public candidate commit.

## Publish an application release

1. Merge the verified change into public `main` and wait for its CI result.
2. Create an annotated version tag on that tested commit, push the tag, and publish
   a GitHub release with artifacts built from that tag.
3. State installation instructions, new behavior, known limitations, and validation
   evidence in the release notes. Check the resulting source archive and assets.
4. Install the published artifact in a clean environment and verify the version,
   launch, and representative workflows.
5. Delete temporary release branches after merging; retain `main` and release tags.

Treat published tags and release assets as immutable. Documentation-only maintenance
can be published on `main` without retagging the application or replacing its wheels.
Improved example downloads can likewise follow `main`; identify that distinction in
the docs when tagged packages still create an older bundle layout.

## Documentation publication

The documentation workflow builds MkDocs and deploys an artifact to GitHub Pages
from `main`. No `gh-pages` branch is needed. The canonical site is
<https://rayanc72.github.io/hybrid-perovskite-studio/>. Verify its home page, tutorials,
images, and example downloads after a deployment.

## PyPI is a separate publication

A GitHub release or documentation deployment does not publish to PyPI. Publish there
only as an explicitly selected release step, after reviewing the distribution and
package credentials. Until then, state the two versions clearly: GitHub **0.3.0**,
PyPI **0.2.1**. Do not imply that a GitHub-only update changes `pip install` results.
