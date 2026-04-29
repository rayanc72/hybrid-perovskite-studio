"""Streamlit-free molecular dynamics parsing helpers for backend workflows."""

from __future__ import annotations

from io import BytesIO
import re

import pandas as pd


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
