from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest

from hps.examples import build_example_bundle, list_example_projects, load_example_project
from hps.ui.navigation import NAVIGATION_REGISTRY


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
        assert "README.md" in names
        guide = archive.read("README.md").decode("utf-8")
        for step in manifest["guide"]:
            assert step["action"] in guide
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


@pytest.mark.parametrize("project_id", ["structure", "electronic", "dynamics"])
def test_example_guide_routes_exist_in_current_navigation(project_id: str) -> None:
    for step in load_example_project(project_id)["guide"]:
        workspace = NAVIGATION_REGISTRY[step["workspace"]]
        if "view" not in step:
            assert "group" not in step and "tool" not in step
            continue
        view = workspace["views"][step["view"]]
        section = view["groups"][step["group"]] if "group" in step else view
        if "tool" in step:
            assert step["tool"] in section["tools"]


def test_dynamics_inner_archive_is_a_single_uploadable_trajectory() -> None:
    with zipfile.ZipFile(BytesIO(build_example_bundle("dynamics"))) as project:
        with zipfile.ZipFile(BytesIO(project.read("trajectory-frames.zip"))) as frames:
            names = frames.namelist()
            assert len(names) == 101
            assert names == sorted(names)
            assert names[0] == "frames/geometry-005364.in"
            assert names[-1] == "frames/geometry-005464.in"
            for name in names:
                assert frames.read(name) == project.read(f"data/md/{name}")
