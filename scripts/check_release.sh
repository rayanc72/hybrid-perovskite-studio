#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"

export MPLBACKEND="${MPLBACKEND:-Agg}"

"${PYTHON_BIN}" -m ruff check \
  src/hps/api src/hps/core src/hps/io src/hps/services \
  src/hps/ui/app_main.py src/hps/ui/backend_workflows.py \
  src/hps/ui/workspaces/structure \
  src/hps/app.py src/hps/cli.py src/hps/__init__.py src/hps/__main__.py tests \
  --select F
"${PYTHON_BIN}" -m pytest -q
"${PYTHON_BIN}" -m mkdocs build --strict --site-dir tmp/release-site
"${PYTHON_BIN}" -m build

echo "Release checks passed."
