"""Generate documentation downloads from the validated packaged examples."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hps.examples import build_example_bundle, list_example_projects  # noqa: E402


def main() -> None:
    destination = ROOT / "docs" / "downloads"
    destination.mkdir(parents=True, exist_ok=True)
    for project in list_example_projects():
        project_id = str(project["id"])
        target = destination / f"hps-example-{project_id}.zip"
        target.write_bytes(build_example_bundle(project_id))
        print(f"Built {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
