from __future__ import annotations

import io
import zipfile

import pytest

from hps.core.electronic import parse_band_payload, parse_spin_texture_payload
from hps.core.md import inspect_trajectory_archive, prepare_trajectory_exports


def test_band_payload_builds_reusable_segments() -> None:
    result = parse_band_payload(
        [
            {
                "name": "band0001.out",
                "content": b"1 0 0 0 1 -2 0 1\n2 0.5 0 0 1 -1 0 2\n",
            }
        ],
        energy_shift=1.0,
    )
    assert result["segment_count"] == 1
    assert result["band_count"] == 2
    assert result["segments"][0]["energies"][0] == [-3.0, 0.0]


def test_spin_texture_payload_reports_state_range() -> None:
    result = parse_spin_texture_payload(
        [
            {
                "name": "spin_texture.dat",
                "content": (
                    b"1 0 0 0 7 -1 0.1 0.2 0.3\n"
                    b"2 0.1 0 0 9 1 0.4 0.5 0.6\n"
                ),
            }
        ]
    )
    assert result["state_range"] == [7, 9]
    assert result["row_count"] == 2


def test_trajectory_archive_is_validated_and_inventoried() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("frames/frame_0001.in", "atom 0 0 0 H\n")
        handle.writestr("frames/frame_0002.in", "atom 0 0 0 H\n")
    result = inspect_trajectory_archive(archive.getvalue(), timestep_fs=2.0)
    assert result["frame_count"] == 2
    assert result["estimated_duration_ps"] == pytest.approx(0.002)


def test_trajectory_archive_rejects_archives_without_frames() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("README.txt", "no trajectory")
    with pytest.raises(ValueError, match="no supported structure frames"):
        inspect_trajectory_archive(archive.getvalue(), timestep_fs=1.0)


def test_trajectory_exports_keep_frame_metrics_out_of_summary() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("frames/geometry-0001.in", "atom 0 0 0 H\n")
        handle.writestr("frames/geometry-0002.in", "atom 0.1 0 0 H\n")

    summary, exports = prepare_trajectory_exports(archive.getvalue(), timestep_fs=0.5)

    assert "metrics" not in summary
    assert summary["frame_count"] == 2
    exports_by_name = {item["name"]: item for item in exports}
    assert set(exports_by_name) == {"metrics_csv", "first_frame", "last_frame"}
    assert b"time_ps" in exports_by_name["metrics_csv"]["data"]
    assert exports_by_name["first_frame"]["data"] == b"atom 0 0 0 H\n"
    assert exports_by_name["last_frame"]["data"] == b"atom 0.1 0 0 H\n"
