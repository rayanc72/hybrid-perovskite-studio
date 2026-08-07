"""Streamlit-free molecular dynamics parsing helpers for backend workflows."""

from __future__ import annotations

import re
import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd
from ase.io import read as read_structure

from hps.io.archives import safe_extract_zip


def try_float_conversion(value):
    try:
        return float(value)
    except ValueError:
        return None


def extract_md_status(lines, idx, prev_te):
    idx += 2
    time = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])
    idx += 1
    free_energy = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])
    idx += 1
    temperature = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])
    idx += 1
    kinetic_energy = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])
    idx += 1
    total_energy = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])
    idx += 1
    conserved_h = try_float_conversion(lines[idx].decode().split(":")[1].strip().split()[0])

    total_energy_change = total_energy - prev_te if prev_te is not None else 0.0
    row = {
        "Time [ps]": time,
        "Temperature [K]": temperature,
        "E_tot (electronic) [eV]": free_energy,
        "E_kin (nuclei) [eV]": kinetic_energy,
        "Total Energy [eV]": total_energy,
        "Total Energy Change [eV]": total_energy_change,
        "Conserved_Hamiltonian [eV]": conserved_h,
    }
    return idx, row, total_energy


def extract_data_from_stream(stream, prev_te=None):
    data = []
    lines = stream.readlines()

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.startswith(b"#"):
            if b"Initial conditions for Born-Oppenheimer Molecular Dynamics:" in line:
                idx, row, prev_te = extract_md_status(lines, idx, prev_te)
                data.append(row)
            elif b"Advancing structure using Born-Oppenheimer Molecular Dynamics" in line:
                idx += 1
                idx, row, prev_te = extract_md_status(lines, idx, prev_te)
                data.append(row)
        idx += 1

    return data, prev_te


def parse_md_outputs(files: list[dict[str, bytes]]) -> dict[str, object]:
    all_data = []
    prev_te = None

    sorted_files = sorted(
        files,
        key=lambda item: int(re.findall(r"\d+", item["name"])[0]) if re.findall(r"\d+", item["name"]) else 0,
    )

    for file in sorted_files:
        buffer = BytesIO(file["content"])
        data, prev_te = extract_data_from_stream(buffer, prev_te)
        all_data.extend(data)

    dataframe = pd.DataFrame(all_data)
    return {
        "table": dataframe.to_dict(orient="records"),
        "columns": list(dataframe.columns),
        "file_count": len(sorted_files),
        "row_count": int(len(dataframe)),
    }


def inspect_trajectory_archive(
    content: bytes, timestep_fs: float, *, include_frame_exports: bool = False
) -> dict[str, object]:
    """Validate and inventory a trajectory archive outside the Streamlit process."""

    if timestep_fs <= 0:
        raise ValueError("timestep_fs must be positive.")
    with tempfile.TemporaryDirectory(prefix="hps-trajectory-backend-") as tmpdir:
        root = Path(tmpdir).resolve()
        paths = safe_extract_zip(BytesIO(content), root)
        files = sorted(path for path in paths if path.is_file())
        geometry_files = [
            path for path in files
            if path.suffix.lower() in {".in", ".cif", ".xyz", ".pdb"}
        ]
        if not geometry_files:
            raise ValueError("Trajectory archive contains no supported structure frames.")
        sizes = [path.stat().st_size for path in files]
        frame_count = len(geometry_files)
        metrics = []
        expected_atoms = None
        for frame_index, path in enumerate(geometry_files):
            atoms = read_structure(path)
            if expected_atoms is None:
                expected_atoms = len(atoms)
            elif len(atoms) != expected_atoms:
                raise ValueError("Trajectory frames do not contain a consistent atom count.")
            center = atoms.get_center_of_mass()
            metrics.append(
                {
                    "frame": frame_index,
                    "name": path.relative_to(root).as_posix(),
                    "atom_count": len(atoms),
                    "formula": atoms.get_chemical_formula(),
                    "cell_volume": float(atoms.get_volume()) if any(atoms.pbc) else None,
                    "center_of_mass": [float(value) for value in center],
                    "time_ps": float(frame_index * timestep_fs / 1000.0),
                }
            )
        result = {
            "file_count": len(files),
            "frame_count": frame_count,
            "total_uncompressed_bytes": int(sum(sizes)),
            "timestep_fs": float(timestep_fs),
            "estimated_duration_ps": float(max(0, frame_count - 1) * timestep_fs / 1000.0),
            "frame_names": [path.relative_to(root).as_posix() for path in geometry_files],
            "metrics": metrics,
            "atom_count": int(expected_atoms or 0),
        }
        if include_frame_exports:
            result["_frame_exports"] = [
                (geometry_files[0].name, geometry_files[0].suffix, geometry_files[0].read_bytes()),
                (
                    geometry_files[-1].name,
                    geometry_files[-1].suffix,
                    geometry_files[-1].read_bytes(),
                ),
            ]
        return result


def prepare_trajectory_exports(
    content: bytes, timestep_fs: float
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Build a compact trajectory summary and reusable downloadable artifacts."""

    inventory = inspect_trajectory_archive(
        content, timestep_fs, include_frame_exports=True
    )
    metrics = list(inventory.pop("metrics"))
    frame_exports = list(inventory.pop("_frame_exports"))
    exports: list[dict[str, object]] = [
        {
            "name": "metrics_csv",
            "file_name": "trajectory_metrics.csv",
            "content_type": "text/csv",
            "suffix": ".csv",
            "data": pd.DataFrame(metrics).to_csv(index=False).encode("utf-8"),
        }
    ]

    for export_name, (file_name, suffix, data) in zip(
        ("first_frame", "last_frame"), frame_exports
    ):
        exports.append(
            {
                "name": export_name,
                "file_name": file_name,
                "content_type": "text/plain",
                "suffix": suffix or ".txt",
                "data": data,
            }
        )

    return inventory, exports
