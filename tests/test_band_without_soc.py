from __future__ import annotations

import base64
import io
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from hps.core.electronic import parse_band_payload
from hps.domain.electronic_property import (
    parse_band_out_files,
    plot_all_bands,
    process_files,
    scale_data,
)

SOC = b"1 0 0.5 0 1 -2 1 -1 0 1 0 2\n2 0 0 0 1 -1.8 1 -0.8 0 1.2 0 2.2\n"
NO_SOC = b"1 0 0.5 0 2 -1.5 0 1.5\n2 0 0 0 2 -1.4 0 1.6\n"


def upload(name, content):
    file = io.BytesIO(content)
    file.name = name
    return file


@pytest.mark.parametrize(
    "suffix,content,count,occupation",
    [(".out", SOC, 4, 1.0), (".out.no_soc", NO_SOC, 2, 2.0)],
)
def test_parsers_preserve_states_occupations_and_shift(suffix, content, count, occupation):
    files = [{"name": f"band1001{suffix}", "content": content}]
    parsed = parse_band_payload(files, energy_shift=-0.5)
    assert parsed["band_count"] == count
    assert parsed["segments"][0]["occupations"][0][0] == occupation
    expected = np.loadtxt(io.BytesIO(content))[:, 5::2] + 0.5
    file = upload(files[0]["name"], content)
    file.read()  # Parsing must not depend on a previous reader's cursor.
    for _ in range(2):
        np.testing.assert_allclose(parse_band_out_files([file], -0.5)[0], expected.T)
    np.testing.assert_allclose(parsed["segments"][0]["energies"], expected)


def test_no_soc_segments_sort_and_ignore_unrelated_files():
    parsed = parse_band_payload([
        {"name": "band1002.out.no_soc", "content": NO_SOC},
        {"name": "control.in", "content": b"ignored"},
        {"name": "BAND1001.OUT.NO_SOC", "content": NO_SOC},
        {"name": "bandmlk1001.out", "content": b"ignored"},
    ])
    assert [s["name"] for s in parsed["segments"]] == [
        "BAND1001.OUT.NO_SOC", "band1002.out.no_soc"
    ]
    assert parsed["file_variant"] == "no_soc"


def test_parser_rejects_mixed_families_instead_of_concatenating_paths():
    with pytest.raises(ValueError, match="separate datasets"):
        parse_band_payload([
            {"name": "band1001.out", "content": SOC},
            {"name": "band1001.out.no_soc", "content": NO_SOC},
        ])


def test_no_soc_parser_rejects_malformed_pairs():
    with pytest.raises(ValueError, match="occupation/energy pairs"):
        parse_band_payload([{"name": "band1001.out.no_soc", "content": b"1 0 0 0 2 -1 0"}])


def test_soc_no_soc_overlay_uses_independent_band_counts_and_shifts():
    datasets = process_files(
        [[upload("band1001.out", SOC)], [upload("band1001.out.no_soc", NO_SOC)]],
        ["crimson", "blue"], ["SOC", "Without SOC"], [-0.8, -1.4],
    )
    assert [len(d["bands_all_files"][0]) for d in datasets] == [4, 2]
    assert datasets[1]["path_units"] == "fractional"
    np.testing.assert_allclose(datasets[1]["xvals"], [[0, 0.5]])
    np.testing.assert_allclose(datasets[1]["bands_all_files"][0][0], [-0.1, 0])
    fig, ax = plt.subplots()
    try:
        plot_all_bands(ax, datasets, False, 2)
        assert ax.get_legend_handles_labels()[1] == ["SOC", "Without SOC"]
        for fmt in ("png", "pdf"):
            output = io.BytesIO()
            fig.savefig(output, format=fmt)
            assert output.tell() > 1000
    finally:
        plt.close(fig)


def test_no_soc_geometry_control_and_segment_filtering():
    files = [
        upload("band1002.out.no_soc", NO_SOC),
        upload("band1001.out.no_soc", NO_SOC),
        upload("geometry.in", b"lattice_vector 2 0 0\n"
               b"lattice_vector 0 2 0\nlattice_vector 0 0 2\n"),
        upload("control.in", b"output band 0 0.5 0 0 0 0 2 Y G\noutput band 0 0 0 0.5 0 0 2 G X\n"),
    ]
    data = process_files([files], ["blue"], ["No SOC"], [-1.4], selected_segments=[2])[0]
    assert len(data["bands_all_files"]) == 1
    assert data["k_label_reduce"] == ["G", "X"]
    assert data["path_units"] == "1/angstrom"
    np.testing.assert_allclose(data["xvals"], [[0, np.pi / 2]])


def test_scaling_preserves_unequal_segment_sampling():
    data = [{}, {"xvals": [[0, 1], [1, 1.5, 2]], "band_len_tot": [0, 1, 2]}]
    scaled = scale_data(data, [1, 2])
    np.testing.assert_allclose(scaled[1]["xvals"][0], [0, 2])
    np.testing.assert_allclose(scaled[1]["xvals"][1], [2, 3, 4])


UPLOAD_APP = """
import streamlit as st
from hps.domain.electronic_property import get_file_uploads
files, colors, labels, shifts, summaries = get_file_uploads(1, ['blue'])
st.session_state['selected_names'] = [[f.name for f in group] for group in files]
st.session_state['summaries'] = summaries
st.session_state['shifts'] = shifts
"""


def test_uploader_auto_detects_no_soc_and_switches_mixed_uploads():
    app = AppTest.from_string(UPLOAD_APP, default_timeout=30).run()
    assert ".no_soc" in app.file_uploader[0].proto.type
    app.file_uploader[0].upload("band1001.out.no_soc", NO_SOC).run()
    assert not app.exception
    assert app.session_state["shifts"] == [-1.4]
    assert app.session_state["summaries"][0]["band_gap"] == pytest.approx(2.9)
    assert not app.selectbox

    app.file_uploader[0].set_value([
        ("band1001.out.no_soc", NO_SOC, "text/plain"),
        ("band1001.out", SOC, "text/plain"),
    ]).run()
    assert not app.exception
    assert app.session_state["selected_names"] == [["band1001.out"]]
    app.selectbox[0].set_value("no_soc").run()
    assert not app.exception
    assert app.session_state["selected_names"] == [["band1001.out.no_soc"]]
    assert app.session_state["summaries"][0]["band_file_count"] == 1
    assert app.session_state["shifts"] == [-1.4]
    app.file_uploader[0].set_value(None).run()
    assert not app.exception
    assert app.session_state["summaries"] == []


def test_workspace_generates_no_soc_plot_and_exports():
    def run_backend(workflow, payload, *args, **kwargs):
        assert workflow == "electronic_band"
        return parse_band_payload([
            {"name": f["name"], "content": base64.b64decode(f["content_b64"])}
            for f in payload["files"]
        ], payload["energy_shift"])

    app = AppTest.from_string("""
from hps.ui.workspaces.electronic import render_electronic_workspace
render_electronic_workspace(
    plot_polarization_option=False, plot_pdos_option=False, plot_bs_option=True,
    plot_spin_option=False, plot_absorption_option=False,
    render_section_header=lambda *a, **k: None,
)
""", default_timeout=30)
    with patch("hps.ui.workspaces.electronic._run_backend_workflow", side_effect=run_backend):
        app.run()
        app.file_uploader[0].upload("band1001.out.no_soc", NO_SOC).run()
        next(b for b in app.button if b.label == "Generate Band Structure").click().run()
    assert not app.exception
    assert not app.error
    assert len(app.get("image")) == 1
    assert {button.label for button in app.get("download_button")} == {"PNG", "PDF"}
    plt.close("all")
