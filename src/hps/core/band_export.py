"""Tabular band exports with explicit state and momentum references."""

from __future__ import annotations

import re
from io import BytesIO

import numpy as np
import pandas as pd


def parse_relative_states(text: str, *, vbm_state: int, band_count: int) -> list[int]:
    """Read signed offsets and inclusive colon ranges, validating before expansion."""
    if not text.strip():
        raise ValueError("Select at least one state relative to the VBM.")
    minimum, maximum = 1 - vbm_state, band_count - vbm_state
    states = set()
    for token in text.split(","):
        match = re.fullmatch(r"\s*([+-]?\d+)\s*(?::\s*([+-]?\d+)\s*)?", token)
        if match is None:
            raise ValueError("Use integer offsets such as -1,0,1 or inclusive ranges like -2:3.")
        start = int(match[1])
        end = int(match[2]) if match[2] is not None else start
        if end < start:
            raise ValueError("State ranges must be ascending, for example -2:3.")
        if start < minimum or end > maximum:
            raise ValueError(f"State offsets must be between {minimum} and {maximum}.")
        states.update(range(start, end + 1))
    return sorted(states)


def build_band_export_table(
    parsed: dict,
    *,
    dataset_label: str,
    vbm_state: int,
    vbm_energy: float,
    state_offsets: list[int],
    selected_segments: list[int],
    reciprocal_lattice=None,
) -> pd.DataFrame:
    """Export one row per selected state/k-point, retaining the original full path.

    State and segment indices are one-based; offsets are relative to the dataset's
    VBM state. Reciprocal lattice vectors are rows and include the 2*pi factor.
    No plot scaling or energy-window clipping is applied.
    """
    band_count = parsed["band_count"]
    if not isinstance(vbm_state, int) or not 1 <= vbm_state <= band_count:
        raise ValueError("A valid VBM state is required for band export.")
    if not np.isfinite(vbm_energy):
        raise ValueError("A finite VBM energy is required for band export.")
    offsets = sorted(set(state_offsets))
    if not offsets:
        raise ValueError("Select at least one state relative to the VBM.")
    if any(not isinstance(s, int) or not 1 <= vbm_state + s <= band_count for s in offsets):
        raise ValueError("Selected states extend beyond the available bands.")
    segments = set(selected_segments)
    if not segments:
        raise ValueError("Select at least one k-path segment.")
    if any(not isinstance(s, int) or not 1 <= s <= len(parsed["segments"]) for s in segments):
        raise ValueError("Selected k-path segments are outside this dataset.")

    reciprocal = None if reciprocal_lattice is None else np.asarray(reciprocal_lattice)
    if reciprocal is not None and (
        reciprocal.shape != (3, 3) or not np.isfinite(reciprocal).all()
    ):
        raise ValueError("The reciprocal lattice must contain three finite vectors.")
    units = "fractional" if reciprocal is None else "1/angstrom"
    frames = []
    path_start = 0.0
    for segment_index, segment in enumerate(parsed["segments"], start=1):
        fractional = np.asarray(segment["k_points"], dtype=float)
        momentum = fractional if reciprocal is None else fractional @ reciprocal
        distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(momentum, axis=0), axis=1))]
        if segment_index in segments:
            raw_energy = np.asarray(segment["energies"]) + parsed["energy_shift"]
            occupations = np.asarray(segment["occupations"])
            for offset in offsets:
                state = vbm_state + offset
                columns = {
                    "dataset": dataset_label,
                    "source_file": segment["name"],
                    "segment": segment_index,
                    "state": state,
                    "state_relative_to_vbm": offset,
                    "vbm_state": vbm_state,
                    "vbm_energy_eV": vbm_energy,
                    "k_point_index": segment["k_point_index"],
                    "kx_fractional": fractional[:, 0],
                    "ky_fractional": fractional[:, 1],
                    "kz_fractional": fractional[:, 2],
                    "segment_distance": distance,
                    "path_distance": path_start + distance,
                    "momentum_units": units,
                    "occupation": occupations[:, state - 1],
                    "energy_eV": raw_energy[:, state - 1],
                    "energy_relative_to_vbm_eV": raw_energy[:, state - 1] - vbm_energy,
                }
                if reciprocal is not None:
                    for axis, label in enumerate(("kx", "ky", "kz")):
                        columns[f"{label}_inv_angstrom"] = momentum[:, axis]
                frames.append(pd.DataFrame(columns))
        path_start += float(distance[-1])
    return pd.concat(frames, ignore_index=True)


def build_band_comparison_table(datasets: list[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    """Align dataset column groups by file segment and exact fractional k coordinates.

    An outer join preserves different sampling grids without interpolation. Repeated
    coordinates within a segment are matched by occurrence, avoiding Cartesian joins.
    Prefixes must uniquely identify datasets even when their legend labels are equal.
    """
    if not datasets or len({prefix for prefix, _ in datasets}) != len(datasets):
        raise ValueError("Comparison datasets need distinct column prefixes.")
    coordinates = ["kx_fractional", "ky_fractional", "kz_fractional"]
    join_keys = ["segment_id", *coordinates, "k_point_occurrence"]
    point_keys = ["source_file", "k_point_index"]
    state_columns = ["state", "occupation", "energy_eV", "energy_relative_to_vbm_eV"]
    comparison = None
    point_order = []
    for prefix, table in datasets:
        if table.empty:
            raise ValueError(f"{prefix}: select at least one sampled k-point.")
        base = table.drop(columns=["state_relative_to_vbm", *state_columns])
        base = base.drop_duplicates(point_keys).copy()
        base["segment_id"] = base.source_file.str.extract(r"(?i)band(\d{4})\.out", expand=False)
        base["k_point_occurrence"] = base.groupby(["segment_id", *coordinates]).cumcount() + 1
        point_order.append(base[join_keys])
        for offset, states in table.groupby("state_relative_to_vbm", sort=True):
            label = "VBM" if offset == 0 else f"VBM{offset:+d}"
            states = states[point_keys + state_columns].rename(
                columns={column: f"{label}.{column}" for column in state_columns}
            )
            base = base.merge(states, on=point_keys, how="left", validate="one_to_one", sort=False)
        base = base.rename(columns={c: f"{prefix}.{c}" for c in base if c not in join_keys})
        if comparison is None:
            comparison = base
        else:
            comparison = comparison.merge(
                base, on=join_keys, how="outer", validate="one_to_one", sort=False
            )
    # Put shared alignment fields first. Retain sample order from the first dataset;
    # points unique to later datasets are added without inventing a common path distance.
    ordered_index = pd.concat(point_order).drop_duplicates().set_index(join_keys).index
    return comparison.set_index(join_keys).reindex(ordered_index).reset_index()


def build_band_workbook(datasets: list[tuple[str, pd.DataFrame]]) -> bytes:
    """Write one XLSX sheet per relative state, preserving side-by-side comparisons."""
    import xlsxwriter

    if not datasets or any(table.empty for _, table in datasets):
        raise ValueError("Select at least one state and k-path segment for every dataset.")
    offsets = sorted(set(datasets[0][1]["state_relative_to_vbm"]))
    if any(set(table["state_relative_to_vbm"]) != set(offsets) for _, table in datasets):
        raise ValueError("All datasets must export the same VBM-relative states.")
    output = BytesIO()
    with xlsxwriter.Workbook(output, {
        "in_memory": True,
        "strings_to_formulas": False,
        "strings_to_urls": False,
    }) as workbook:
        header = workbook.add_format({
            "bold": True, "font_color": "#FFFFFF", "bg_color": "#00539B",
            "text_wrap": True, "valign": "top",
        })
        number = workbook.add_format({"num_format": "0.0000000"})
        for offset in offsets:
            name = "VBM" if offset == 0 else f"VBM{offset:+d}"
            state_tables = [
                (prefix, table.loc[table["state_relative_to_vbm"] == offset])
                for prefix, table in datasets
            ]
            table = (
                build_band_comparison_table(state_tables)
                if len(state_tables) > 1 else state_tables[0][1]
            )
            if len(table) > 1_048_575 or len(table.columns) > 16_384:
                raise ValueError(
                    "The selection exceeds Excel's worksheet limits; select less data."
                )
            sheet = workbook.add_worksheet(name)
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, len(table), len(table.columns) - 1)
            sheet.set_row(0, 75)
            sheet.write_row(0, 0, list(table.columns), header)
            for column_index, column in enumerate(table.columns):
                is_float = any(token in column for token in (
                    "energy", "distance", "fractional", "inv_angstrom", "occupation",
                ))
                sheet.set_column(column_index, column_index, 24, number if is_float else None)
            # Write numerical cells as numbers; unmatched comparison samples remain empty.
            for row_index, row in enumerate(table.itertuples(index=False, name=None), start=1):
                sheet.write_row(row_index, 0, [None if pd.isna(value) else value for value in row])
    return output.getvalue()
