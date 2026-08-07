"""Packaged, provenance-aware example projects for Hybrid Perovskite Studio."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path

EXAMPLES_ROOT = Path(__file__).resolve().parent
PROJECTS_ROOT = EXAMPLES_ROOT / "projects"


def list_example_projects() -> list[dict[str, object]]:
    """Return compact metadata for every packaged guided example."""

    return [
        {
            "id": manifest["id"],
            "title": manifest["title"],
            "description": manifest["description"],
        }
        for manifest in (_load_manifest(path) for path in sorted(PROJECTS_ROOT.glob("*.json")))
    ]


def load_example_project(project_id: str) -> dict[str, object]:
    """Load and validate a packaged example manifest by identifier."""

    if not project_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in project_id
    ):
        raise ValueError(
            "Example project identifiers may contain lowercase letters, digits, - and _."
        )
    path = PROJECTS_ROOT / f"{project_id}.json"
    if not path.is_file():
        raise KeyError(f"Unknown example project: {project_id}")
    manifest = _load_manifest(path)
    validate_example_project(manifest)
    return manifest


def validate_example_project(manifest: dict[str, object]) -> None:
    """Validate file counts and aggregate checksums declared by a manifest."""

    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported example project schema version.")
    for file_set in manifest.get("file_sets", []):
        paths = _expand_file_set(file_set)
        if len(paths) != int(file_set["count"]):
            raise ValueError(f"Unexpected file count for example role {file_set['role']!r}.")
        digest = _aggregate_digest(paths)
        if digest != file_set["sha256"]:
            raise ValueError(f"Checksum mismatch for example role {file_set['role']!r}.")


def build_example_bundle(project_id: str) -> bytes:
    """Return a self-contained ZIP containing a guide, provenance, and example inputs."""

    manifest = load_example_project(project_id)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("project.json", json.dumps(manifest, indent=2, sort_keys=True))
        for shared_name in ("PROVENANCE.md", "expected_results.json"):
            handle.write(EXAMPLES_ROOT / "data" / shared_name, shared_name)
        for file_set in manifest["file_sets"]:
            for path in _expand_file_set(file_set):
                handle.write(path, path.relative_to(EXAMPLES_ROOT).as_posix())
    return archive.getvalue()


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _expand_file_set(file_set: dict[str, object]) -> list[Path]:
    root = EXAMPLES_ROOT.resolve()
    path = (root / str(file_set["path"])).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Example file path escapes the packaged examples directory.")
    pattern = str(file_set.get("pattern", "*"))
    paths = (
        sorted(item for item in path.glob(pattern) if item.is_file()) if path.is_dir() else [path]
    )
    if not paths or any(not item.is_file() for item in paths):
        raise ValueError(f"Example file set is missing: {file_set['path']}")
    return paths


def _aggregate_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    data_root = EXAMPLES_ROOT / "data"
    for path in paths:
        digest.update(path.relative_to(data_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List or build packaged HPS example projects.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List available example projects.")
    build_parser = subparsers.add_parser("build", help="Build a self-contained example ZIP.")
    build_parser.add_argument("project_id")
    build_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "list":
        for project in list_example_projects():
            print(f"{project['id']}: {project['title']}")
        return 0

    output = args.output or Path(f"hps-example-{args.project_id}.zip")
    output.write_bytes(build_example_bundle(args.project_id))
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
