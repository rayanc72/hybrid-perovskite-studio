from __future__ import annotations

import io
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from hps.core.band_export import (
    build_band_comparison_table,
    build_band_export_table,
    build_band_workbook,
    parse_relative_states,
)
from hps.core.electronic import parse_band_payload


def band_payload(suffix=".out", occupied=1):
    # The VBM is state 2 at the end of segment 1. Segment 2 has a lower maximum.
    return parse_band_payload([
        {"name": f"band1002{suffix}", "content": (
            f"1 0.5 0 0 {occupied} -4 {occupied} -2 0 2 0 3\n"
            f"2 0.5 0.5 0 {occupied} -3 {occupied} -1.5 0 3 0 4\n"
        ).encode()},
        {"name": f"band1001{suffix}", "content": (
            f"1 0 0 0 {occupied} -3 {occupied} -2 0 1 0 2\n"
            f"2 0.25 0 0 {occupied} -2 {occupied} -1.5 0 2 0 3\n"
            f"3 0.5 0 0 {occupied} -2 {occupied} -1 0 2 0 3\n"
        ).encode()},
    ], energy_shift=-0.5)


def export(parsed=None, **kwargs):
    arguments = dict(
        dataset_label="Example", vbm_state=2, vbm_energy=-1.0,
        state_offsets=[-1, 0, 1], selected_segments=[2],
    )
    arguments.update(kwargs)
    return build_band_export_table(parsed or band_payload(), **arguments)


def test_relative_state_ranges_are_inclusive_signed_and_deduplicated():
    assert parse_relative_states("-2:1, +2,0", vbm_state=3, band_count=5) == [-2, -1, 0, 1, 2]


@pytest.mark.parametrize("text", ["", "1.5", "VBM", "0,", "1:-1", "-2", "3", "0:999999999"])
def test_bad_state_selection_is_rejected_before_expansion(text):
    with pytest.raises(ValueError):
        parse_relative_states(text, vbm_state=2, band_count=4)


@pytest.mark.parametrize("suffix,occupation", [(".out", 1), (".out.no_soc", 2)])
def test_csv_selects_exact_states_segments_and_global_vbm_reference(suffix, occupation):
    table = export(band_payload(suffix, occupation))
    assert len(table) == 6
    assert table["segment"].unique().tolist() == [2]
    assert table["source_file"].unique().tolist() == [f"band1002{suffix}"]
    assert table["state"].tolist() == [1, 1, 2, 2, 3, 3]
    assert table["state_relative_to_vbm"].tolist() == [-1, -1, 0, 0, 1, 1]
    assert table["k_point_index"].tolist() == [1, 2] * 3
    vbm = table.loc[table.state_relative_to_vbm == 0]
    np.testing.assert_allclose(vbm.energy_eV, [-2, -1.5])
    np.testing.assert_allclose(vbm.energy_relative_to_vbm_eV, [-1, -0.5])
    np.testing.assert_allclose(vbm.occupation, occupation)
    np.testing.assert_allclose(vbm.path_distance, [0.5, 1.0])
    np.testing.assert_allclose(vbm.segment_distance, [0, 0.5])
    assert set(table.momentum_units) == {"fractional"}
    assert "kx_inv_angstrom" not in table
    pd.testing.assert_frame_equal(pd.read_csv(io.StringIO(table.to_csv(index=False))), table)


def test_cartesian_momentum_uses_row_vectors_and_preserves_fractional_coordinates():
    reciprocal = np.array([[2, 1, 0], [0, 3, 1], [1, 0, 4]], dtype=float)
    table = export(state_offsets=[0], reciprocal_lattice=reciprocal)
    np.testing.assert_allclose(table[["kx_inv_angstrom", "ky_inv_angstrom", "kz_inv_angstrom"]],
                               [[1, 0.5, 0], [1, 2, 0.5]])
    np.testing.assert_allclose(table[["kx_fractional", "ky_fractional", "kz_fractional"]],
                               [[0.5, 0, 0], [0.5, 0.5, 0]])
    np.testing.assert_allclose(table.segment_distance, [0, np.sqrt(10) / 2])
    np.testing.assert_allclose(table.path_distance,
                               [np.sqrt(5) / 2, (np.sqrt(5) + np.sqrt(10)) / 2])
    assert set(table.momentum_units) == {"1/angstrom"}


@pytest.mark.parametrize("arguments", [
    {"state_offsets": []}, {"state_offsets": [-2]}, {"state_offsets": [3]},
    {"selected_segments": []}, {"selected_segments": [0]}, {"selected_segments": [3]},
    {"vbm_state": 0}, {"vbm_energy": float("nan")}, {"reciprocal_lattice": [[1, 2, 3]]},
])
def test_invalid_export_selection_is_rejected(arguments):
    with pytest.raises(ValueError):
        export(**arguments)


def test_side_by_side_maps_each_vbm_and_handles_different_sampling_without_interpolation():
    soc = export(state_offsets=[0, 1], selected_segments=[1])
    no_soc_parsed = parse_band_payload([{
        "name": "band1001.out.no_soc",
        "content": b"1 0 0 0 2 -5 0 -2\n2 0.5 0 0 2 -4 0 -1\n",
    }])
    no_soc = export(
        no_soc_parsed, dataset_label="No SOC", vbm_state=1, vbm_energy=-4,
        state_offsets=[0, 1], selected_segments=[1],
    )
    comparison = build_band_comparison_table([("soc", soc), ("no_soc", no_soc)])
    assert len(comparison) == 3
    np.testing.assert_allclose(comparison.kx_fractional, [0, 0.25, 0.5])
    np.testing.assert_allclose(comparison["soc.VBM.state"], [2, 2, 2])
    np.testing.assert_allclose(comparison["no_soc.VBM.state"], [1, np.nan, 1])
    np.testing.assert_allclose(comparison["soc.VBM+1.energy_relative_to_vbm_eV"], [2, 3, 3])
    np.testing.assert_allclose(comparison["no_soc.VBM+1.energy_relative_to_vbm_eV"],
                               [2, np.nan, 3])
    assert comparison["no_soc.VBM.energy_eV"].iloc[-1] == -4


def test_comparison_preserves_repeated_coordinates_without_duplicate_join_rows():
    parsed = parse_band_payload([{
        "name": "band1001.out", "content":
        b"1 0 0 0 1 -2 0 1\n2 0.5 0 0 1 -1 0 2\n3 0 0 0 1 -2 0 1\n",
    }])
    table = export(parsed, vbm_state=1, state_offsets=[0], selected_segments=[1])
    comparison = build_band_comparison_table([("a", table), ("b", table)])
    assert len(comparison) == 3
    assert comparison.k_point_occurrence.tolist() == [1, 1, 2]


def test_comparison_keeps_different_file_segments_separate():
    a = export(selected_segments=[1], state_offsets=[0])
    b = a.copy()
    b["source_file"] = "band1002.out.no_soc"
    comparison = build_band_comparison_table([("a", a), ("b", b)])
    assert len(comparison) == 6
    assert set(comparison.segment_id) == {"1001", "1002"}
    assert not (comparison["a.VBM.state"].notna() & comparison["b.VBM.state"].notna()).any()


def test_workbook_separates_states_and_preserves_numeric_cells_and_missing_samples():
    first = export(selected_segments=[1], state_offsets=[-1, 0, 1])
    second = first.loc[first.k_point_index != 2].copy()
    second["source_file"] = "band1001.out.no_soc"
    second["state"] += 10
    second["vbm_state"] += 10
    data = build_band_workbook([("soc", first), ("no_soc", second)])
    book = load_workbook(io.BytesIO(data))
    assert book.sheetnames == ["VBM-1", "VBM", "VBM+1"]
    for name, expected_state in [("VBM-1", 1), ("VBM", 2), ("VBM+1", 3)]:
        sheet = book[name]
        assert sheet.max_row == 4  # Header + three k-points, including the unmatched sample.
        assert sheet.freeze_panes == "A2"
        assert sheet.auto_filter.ref
        columns = {cell.value: cell.column for cell in sheet[1]}
        assert not any(f".{other}." in c for other in book.sheetnames if other != name
                       for c in columns)
        assert sheet.cell(2, columns[f"soc.{name}.state"]).value == expected_state
        assert sheet.cell(2, columns[f"no_soc.{name}.state"]).value == expected_state + 10
        assert sheet.cell(3, columns[f"no_soc.{name}.energy_eV"]).value is None
        energy = sheet.cell(2, columns[f"soc.{name}.energy_eV"])
        assert energy.data_type == "n"
        assert energy.value == first.loc[first.state == expected_state, "energy_eV"].iloc[0]
    book.close()


def test_single_dataset_workbook_has_only_selected_state_sheets_and_literal_labels():
    table = export(state_offsets=[-1, 1], dataset_label="=1+1")
    book = load_workbook(io.BytesIO(build_band_workbook([("a", table)])))
    assert book.sheetnames == ["VBM-1", "VBM+1"]
    for offset, name in [(-1, "VBM-1"), (1, "VBM+1")]:
        rows = list(book[name].values)
        frame = pd.DataFrame(rows[1:], columns=rows[0])
        assert set(frame.state_relative_to_vbm) == {offset}
        assert set(frame.segment) == {2}
        assert book[name]["A2"].value == "=1+1"
        assert book[name]["A2"].data_type == "s"
    book.close()


def test_workbook_rejects_inconsistent_state_selection():
    with pytest.raises(ValueError, match="same VBM-relative states"):
        build_band_workbook([("a", export(state_offsets=[0])), ("b", export(state_offsets=[1]))])


APP = """
import streamlit as st
from hps.ui.workspaces.electronic import render_electronic_workspace
# AppTest does not serialize interactive tab selection between reruns yet.
st.session_state["band_studio_tab"] = "Excel export"
render_electronic_workspace(
    plot_polarization_option=False, plot_pdos_option=False, plot_bs_option=True,
    plot_spin_option=False, plot_absorption_option=False,
    render_section_header=lambda *a, **k: None,
)
"""


def test_xlsx_ui_updates_selection_and_blocks_stale_downloads_without_plotting():
    content = b"1 0 0 0 2 -2 2 -1 0 1\n2 0.5 0 0 2 -1.5 2 -0.5 0 2\n"
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert "Excel export" in [tab.label for tab in app.tabs]
    app.file_uploader[0].set_value([
        ("band1001.out.no_soc", content, "text/plain"),
        ("band1002.out.no_soc", content, "text/plain"),
    ]).run()
    assert not app.exception
    # Capture the real bytes passed to the download widget, while rendering it normally.
    import streamlit as st
    original = st.download_button
    downloads = []

    def capture(label, **kwargs):
        if label == "Download Excel workbook (.xlsx)":
            downloads.append(kwargs["data"])
        return original(label, **kwargs)

    with patch("hps.ui.workspaces.electronic.st.download_button", side_effect=capture):
        app.session_state["band_studio_tab"] = "Excel export"
        app.run()
        assert not app.exception
        assert not app.error
        sheets = pd.read_excel(io.BytesIO(downloads[-1]), sheet_name=None)
        assert list(sheets) == ["VBM", "VBM+1"]
        assert sum(map(len, sheets.values())) == 8
        app.text_input(key="band_csv_states").set_value("-1:0").run()
        segments = next(w for w in app.multiselect if w.label == "K-path segments to export")
        segments.set_value(["1002"]).run()
        assert not app.exception
        sheets = pd.read_excel(io.BytesIO(downloads[-1]), sheet_name=None)
        assert list(sheets) == ["VBM-1", "VBM"]
        table = pd.concat(sheets.values())
        assert len(table) == 4
        assert set(table.segment) == {2}
        assert set(table.state) == {1, 2}
        assert set(table.state_relative_to_vbm) == {-1, 0}
        app.text_input(key="band_csv_states").set_value("9999").run()
        assert app.error
        assert not app.get("download_button")
        app.text_input(key="band_csv_states").set_value("0").run()
        assert not app.error
        segments = next(w for w in app.multiselect if w.label == "K-path segments to export")
        segments.set_value([]).run()
        assert app.error
        assert not app.get("download_button")
    assert not app.exception


def test_xlsx_dataset_switch_uses_each_datasets_vbm_state():
    soc = b"1 0 0 0 1 -2 1 -1 0 1\n2 0.5 0 0 1 -1.5 1 -0.5 0 2\n"
    no_soc = b"1 0 0 0 2 -1.5 0 1.5\n2 0.5 0 0 2 -1.4 0 1.6\n"
    app = AppTest.from_string(APP, default_timeout=30).run()
    app.number_input[0].set_value(2).run()
    app.file_uploader[0].upload("band1001.out", soc)
    app.file_uploader[1].upload("band1001.out.no_soc", no_soc).run()
    import streamlit as st
    original = st.download_button
    downloads = []

    def capture(label, **kwargs):
        if label == "Download Excel workbook (.xlsx)":
            downloads.append(kwargs["data"])
        return original(label, **kwargs)

    with patch("hps.ui.workspaces.electronic.st.download_button", side_effect=capture):
        app.session_state["band_studio_tab"] = "Excel export"
        app.run()
    assert not app.error
    sheets = pd.read_excel(io.BytesIO(downloads[-1]), sheet_name=None)
    assert list(sheets) == ["VBM", "VBM+1"]
    comparison = sheets["VBM"]
    assert len(comparison) == 2
    assert comparison["dataset_1[Data set 1].VBM.state"].tolist() == [2, 2]
    assert comparison["dataset_2[Data set 2].VBM.state"].tolist() == [1, 1]
    np.testing.assert_allclose(
        sheets["VBM+1"]["dataset_2[Data set 2].VBM+1.energy_relative_to_vbm_eV"], [2.9, 3.0]
    )
    assert not app.exception
    assert any("VBM (state 2)" in c.value for c in app.caption)
    app.multiselect[0].set_value([1]).run()
    assert not app.exception
    assert not app.error
    assert any("VBM (state 1)" in c.value for c in app.caption)
    assert app.get("download_button")[0].proto.url.endswith(".xlsx")
