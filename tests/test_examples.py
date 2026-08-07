from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest

from hps.examples import build_example_bundle, list_example_projects, load_example_project


@pytest.mark.parametrize(
    ("project_id", "input_count"),
    [("structure", 1), ("electronic", 10), ("dynamics", 101)],
)
def test_example_projects_validate_and_build(project_id: str, input_count: int) -> None:
    manifest = load_example_project(project_id)
    bundle = build_example_bundle(project_id)

    with zipfile.ZipFile(BytesIO(bundle)) as archive:
        names = archive.namelist()
        bundled_manifest = json.loads(archive.read("project.json"))
        assert bundled_manifest == manifest
        assert "PROVENANCE.md" in names
        assert "expected_results.json" in names
        assert len([name for name in names if name.startswith("data/")]) == input_count


def test_example_catalog_is_stable() -> None:
    assert [project["id"] for project in list_example_projects()] == [
        "dynamics",
        "electronic",
        "structure",
    ]


def test_unknown_example_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown example project"):
        load_example_project("missing")
