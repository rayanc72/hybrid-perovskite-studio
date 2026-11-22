"""CIF downloads convert only the captured transformation result, on demand."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import numpy as np
from ase import Atoms
from ase.io import read, write

from hps.ui.workspaces.structure.transformations import downloads


def _structure() -> Atoms:
    return Atoms(
        "CHH",
        positions=[[1, 2, 3], [1, 2, 4], [1, 3, 3]],
        cell=[[8, 0, 0], [1, 9, 0], [0, 2, 10]],
        pbc=True,
    )


def _assert_same_structure(actual: Atoms, expected: Atoms) -> None:
    assert actual.get_chemical_symbols() == expected.get_chemical_symbols()
    np.testing.assert_allclose(actual.cell, expected.cell, atol=1e-8)
    difference = actual.get_scaled_positions() - expected.get_scaled_positions()
    np.testing.assert_allclose(difference - np.round(difference), 0, atol=1e-8)


def test_single_cif_download_is_deferred_and_preserves_transformation_snapshot():
    atoms = _structure()
    atoms.translate([0.25, 0.5, -0.1])
    expected = atoms.copy()
    with (
        patch.object(downloads.st, "download_button") as button,
        patch.object(downloads, "write", wraps=write) as writer,
    ):
        downloads.create_cif_download_file(atoms, "sample.cif", "_translated")
        writer.assert_not_called()
        options = button.call_args.kwargs
        assert options["file_name"] == "sample_translated.cif"
        assert options["on_click"] == "ignore"
        assert callable(options["data"])
        # Later reruns or operations must not change this download's result.
        atoms.translate([3, 2, 1])
        content = options["data"]()
        writer.assert_called_once()
    _assert_same_structure(read(io.BytesIO(content), format="cif"), expected)


def test_labelled_cif_preserves_custom_labels_with_unique_site_names():
    with patch.object(downloads.st, "download_button") as button:
        downloads.create_cif_download_file(
            _structure(),
            "geometry.in",
            atom_label_overrides={1: "Hgroup", 2: "Hgroup"},
        )
        content = button.call_args.kwargs["data"]()
    restored = read(io.BytesIO(content), format="cif", store_tags=True)
    assert restored.info["_atom_site_label"] == ["C1", "Hgroup_2", "Hgroup_3"]
    _assert_same_structure(restored, _structure())


def test_cif_archive_is_deferred_and_contains_all_generated_snapshots():
    first = _structure()
    second = first.copy()
    second.positions[0] += [0.25, 0.5, 0.75]
    expected = [first.copy(), second.copy()]
    with (
        patch.object(downloads.st, "download_button") as button,
        patch.object(downloads, "write", wraps=write) as writer,
    ):
        downloads.create_cif_archive_download(
            [("0_deg/first.cif", first), ("90_deg/second.cif", second)],
            "rotated_structures_cif.zip",
            download_label="Download CIF ZIP",
        )
        writer.assert_not_called()
        options = button.call_args.kwargs
        assert options["on_click"] == "ignore"
        first.positions[:] = 0
        second.positions[:] = 0
        content = options["data"]()
        assert writer.call_count == 2
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.namelist() == ["0_deg/first.cif", "90_deg/second.cif"]
        for name, atoms in zip(archive.namelist(), expected):
            _assert_same_structure(read(io.BytesIO(archive.read(name)), format="cif"), atoms)
