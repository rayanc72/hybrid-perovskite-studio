from __future__ import annotations

import io
import json
import zipfile

import numpy as np
import pytest

from hps.core.electronic import (
    parse_band_payload,
    parse_pdos_payload,
    parse_spin_texture_payload,
)
from hps.core.md import inspect_trajectory_archive
from hps.core.structure import summarize_structure_upload
from hps.examples import EXAMPLES_ROOT

FIXTURES = EXAMPLES_ROOT / "data"
EXPECTED = json.loads((FIXTURES / "expected_results.json").read_text())


def _named_files(directory: str, pattern: str) -> list[dict[str, object]]:
    return [
        {"name": path.name, "content": path.read_bytes()}
        for path in sorted((FIXTURES / directory).glob(pattern))
    ]


def test_structure_reference_result() -> None:
    path = FIXTURES / "structure" / "MC3I_PbI_100K.in"
    result = summarize_structure_upload(file_name=path.name, file_bytes=path.read_bytes())
    expected = EXPECTED["structure"]
    assert result["formula"] == expected["formula"]
    assert result["atom_count"] == expected["atom_count"]
    assert result["molecule_group_count"] == expected["molecule_group_count"]
    assert result["space_group"] == expected["space_group"]
    assert result["space_group_number"] == expected["space_group_number"]
    assert np.allclose(result["lattice_vectors"], expected["lattice_vectors"])


def test_pdos_reference_result() -> None:
    result = parse_pdos_payload(
        _named_files("pdos", "*.dat"),
        combination_text="PbI = Pb(s) + Pb(p) + I",
    )
    expected = EXPECTED["pdos"]
    table = result["pdos_table"]
    energy = np.asarray([row["Energy"] for row in table])
    total = np.asarray([row["Total DOS"] for row in table])
    nearest_fermi = int(np.abs(energy).argmin())
    assert len(table) == expected["row_count"]
    assert energy.min() == pytest.approx(expected["energy_min"])
    assert energy.max() == pytest.approx(expected["energy_max"])
    assert total.max() == pytest.approx(expected["sampled_total_dos_max"])
    assert energy[total.argmax()] == pytest.approx(expected["sampled_total_dos_peak_energy"])
    assert energy[nearest_fermi] == pytest.approx(expected["nearest_fermi_energy"])
    assert total[nearest_fermi] == pytest.approx(expected["total_dos_nearest_fermi"])


def test_band_reference_results() -> None:
    result = parse_band_payload(_named_files("bands", "*.out"))
    expected = EXPECTED["bands"]
    assert result["segment_count"] == expected["segment_count"]
    assert result["band_count"] == expected["band_count"]
    assert result["energy_range"] == pytest.approx(expected["energy_range"])

    for segment, segment_expected in zip(result["segments"], expected["segments"]):
        occupations = np.asarray(segment["occupations"])
        energies = np.asarray(segment["energies"])
        occupied = energies[occupations > 0.5]
        unoccupied = energies[occupations <= 0.5]
        vbm = float(occupied.max())
        cbm = float(unoccupied.min())
        assert segment["name"] == segment_expected["name"]
        assert len(segment["k_point_index"]) == segment_expected["kpoint_count"]
        assert vbm == pytest.approx(segment_expected["vbm"])
        assert cbm == pytest.approx(segment_expected["cbm"])
        assert cbm - vbm == pytest.approx(segment_expected["gap"])


def test_spin_texture_reference_result() -> None:
    path = FIXTURES / "spin" / "spin_texture.dat"
    result = parse_spin_texture_payload(
        [{"name": path.name, "content": path.read_bytes()}]
    )
    expected = EXPECTED["spin"]
    rows = result["table"]
    norms = np.asarray(
        [
            np.linalg.norm([row["sigma_x"], row["sigma_y"], row["sigma_z"]])
            for row in rows
        ]
    )
    assert result["row_count"] == expected["row_count"]
    assert result["states"] == expected["states"]
    assert len({row["k_point"] for row in rows}) == expected["kpoint_labels"]
    assert min(row["eigenvalue"] for row in rows) == pytest.approx(expected["energy_min"])
    assert max(row["eigenvalue"] for row in rows) == pytest.approx(expected["energy_max"])
    assert norms.max() == pytest.approx(expected["max_spin_norm"])


def test_md_trajectory_reference_result() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in sorted((FIXTURES / "md" / "frames").glob("*.in")):
            handle.writestr(f"frames/{path.name}", path.read_bytes())

    expected = EXPECTED["md"]
    result = inspect_trajectory_archive(
        archive.getvalue(), timestep_fs=expected["timestep_fs"]
    )
    assert result["file_count"] == expected["file_count"]
    assert result["frame_count"] == expected["frame_count"]
    assert result["atom_count"] == expected["atom_count"]
    assert result["total_uncompressed_bytes"] == expected["total_uncompressed_bytes"]
    assert result["timestep_fs"] == pytest.approx(expected["timestep_fs"])
    assert result["estimated_duration_ps"] == pytest.approx(expected["estimated_duration_ps"])
    assert result["estimated_duration_ps"] >= 0.05
    assert result["frame_names"][0] == expected["first_frame"]
    assert result["frame_names"][-1] == expected["last_frame"]
    assert result["metrics"][0]["formula"] == expected["formula"]
    assert result["metrics"][0]["cell_volume"] == pytest.approx(expected["cell_volume"])
    assert result["metrics"][0]["center_of_mass"] == pytest.approx(
        expected["first_center_of_mass"]
    )
    assert result["metrics"][-1]["center_of_mass"] == pytest.approx(
        expected["last_center_of_mass"]
    )
