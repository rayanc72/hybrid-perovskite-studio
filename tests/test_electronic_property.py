from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.domain.electronic_property import (
    add_pdos_combination_traces,
    add_pdos_combinations,
    build_pdos_table,
    detect_pdos_file_roles,
    get_rec_vector,
    get_pdos_combination_labels,
    get_pdos_trace_options,
    parse_pdos_uploads,
    parse_band_out_files,
    plot_bands,
    plot_pdos_streamlit,
    process_control_file,
    prepare_plot_data,
    resolve_spin_texture_plane,
    smooth_pdos_values,
)


def named_upload(name: str, text: str) -> io.StringIO:
    upload = io.StringIO(text)
    upload.name = name
    return upload


class ElectronicPropertyTests(unittest.TestCase):
    def test_bandstructure_handles_mixed_kpoint_counts_per_segment(self) -> None:
        reciprocal = np.eye(3)
        control = io.BytesIO(
            "\n".join(
                [
                    "output band 0.0 0.0 0.0 1.0 0.0 0.0 3 G X",
                    "output band 1.0 0.0 0.0 1.0 1.0 0.0 5 X M",
                ]
            ).encode("utf-8")
        )
        control.name = "control.in"

        _, _, band_len, _, xvals, band_len_tot = process_control_file(control, reciprocal)

        self.assertEqual([len(segment) for segment in xvals], [3, 5])
        self.assertTrue(np.allclose(xvals[0], np.array([0.0, 0.5, 1.0])))
        self.assertTrue(np.allclose(xvals[1], np.array([1.0, 1.25, 1.5, 1.75, 2.0])))
        self.assertTrue(np.allclose(band_len, np.array([1.0, 1.0])))
        self.assertTrue(np.allclose(band_len_tot, np.array([0.0, 1.0, 2.0])))

    def test_plot_bands_accepts_segments_with_different_point_counts(self) -> None:
        uploads = []
        for index, rows in enumerate(
            [
                ["0 0 0 0 1 0.1 1 0.2", "0 0 0 0 1 0.3 1 0.4", "0 0 0 0 1 0.5 1 0.6"],
                [
                    "0 0 0 0 1 1.1 1 1.2",
                    "0 0 0 0 1 1.3 1 1.4",
                    "0 0 0 0 1 1.5 1 1.6",
                    "0 0 0 0 1 1.7 1 1.8",
                    "0 0 0 0 1 1.9 1 2.0",
                ],
            ],
            start=1,
        ):
            upload = io.BytesIO("\n".join(rows).encode("utf-8"))
            upload.name = f"band{index:04d}.out"
            uploads.append(upload)

        bands_all_files = parse_band_out_files(uploads, energyshift=0.0)
        fig, ax = plt.subplots()
        try:
            plot_bands(
                ax,
                bands_all_files,
                xvals=[
                    np.array([0.0, 0.5, 1.0]),
                    np.array([1.0, 1.25, 1.5, 1.75, 2.0]),
                ],
                plot_color="black",
            )
        finally:
            plt.close(fig)

        self.assertEqual(len(ax.lines), 5)

    def test_detect_pdos_file_roles_matches_fhi_aims_files_case_insensitively(self) -> None:
        roles = detect_pdos_file_roles(
            [
                named_upload("KS_DOS_total.DAT", "0 1\n"),
                named_upload("Pb_l_proj_dos.dat", "0 1 2 3\n"),
                named_upload("notes.txt", "ignored\n"),
            ]
        )

        self.assertEqual(roles["total"], ["KS_DOS_total.DAT"])
        self.assertEqual(roles["projected"], [{"name": "Pb_l_proj_dos.dat", "element": "Pb"}])
        self.assertEqual(roles["unrecognized"], ["notes.txt"])

    def test_parse_pdos_uploads_builds_combined_table(self) -> None:
        total = named_upload("KS_DOS_total.dat", "0.0 10.0\n1.0 11.0\n")
        pb = named_upload("Pb_l_proj_dos.dat", "0.0 1.0 2.0 3.0\n1.0 1.5 2.5 3.5\n")
        iodine = named_upload("I_l_proj_dos.dat", "0.0 4.0\n1.0 5.0\n")

        dos_data, table, roles = parse_pdos_uploads([total, pb, iodine])

        self.assertIn("Total", dos_data)
        self.assertIn("Pb", dos_data)
        self.assertIn("I", dos_data)
        self.assertEqual(roles["unrecognized"], [])
        self.assertEqual(list(table.columns), ["Energy", "Total DOS", "Pb", "Pb(s)", "Pb(p)", "I"])
        self.assertTrue(np.allclose(table["Energy"], np.array([0.0, 1.0])))
        self.assertTrue(np.allclose(table["Pb(s)"], np.array([2.0, 2.5])))
        self.assertTrue(np.allclose(table["Pb(p)"], np.array([3.0, 3.5])))

    def test_parse_pdos_uploads_rejects_missing_total_dos(self) -> None:
        bromine = named_upload("Br_l_proj_dos.dat", "0.0 1.0\n")

        with self.assertRaisesRegex(ValueError, "KS_DOS_total"):
            parse_pdos_uploads([bromine])

    def test_parse_pdos_uploads_rejects_unrecognized_only_uploads(self) -> None:
        notes = named_upload("notes.txt", "not pdos data\n")

        with self.assertRaisesRegex(ValueError, "No FHI-aims PDOS files"):
            parse_pdos_uploads([notes])

    def test_parse_pdos_uploads_rejects_malformed_projected_columns(self) -> None:
        total = named_upload("KS_DOS_total.dat", "0.0 10.0\n")
        lead = named_upload("Pb_l_proj_dos.dat", "0.0 1.0 2.0\n")

        with self.assertRaisesRegex(ValueError, "at least 4 numeric columns"):
            parse_pdos_uploads([total, lead])

    def test_build_pdos_table_rejects_mismatched_energy_axis(self) -> None:
        dos_data = {
            "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
            "I": np.array([[0.0, 4.0], [2.0, 5.0]]),
        }

        with self.assertRaisesRegex(ValueError, "energy values do not match"):
            build_pdos_table(dos_data)

    def test_plot_pdos_streamlit_creates_total_orbital_and_halide_traces(self) -> None:
        dos_data = {
            "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
            "Pb": np.array([[0.0, 1.0, 2.0, 3.0], [1.0, 1.5, 2.5, 3.5]]),
            "I": np.array([[0.0, 4.0], [1.0, 5.0]]),
        }

        fig = plot_pdos_streamlit(
            dos_data,
            shift=0.5,
            plot_range=(-1.0, 2.0),
            dos_range=(0.0, 12.0),
            figure_height=650,
        )

        self.assertEqual([trace.name for trace in fig.data], ["Total DOS", "Pb(s)", "Pb(p)", "I"])
        self.assertEqual(fig.data[0].line.color, "black")
        self.assertTrue(np.allclose(fig.data[0].y, np.array([0.5, 1.5])))
        self.assertEqual(fig.layout.height, 650)
        self.assertEqual(tuple(fig.layout.yaxis.range), (-1.0, 2.0))
        self.assertEqual(tuple(fig.layout.xaxis.range), (0.0, 12.0))

    def test_get_pdos_trace_options_lists_plot_trace_names(self) -> None:
        dos_data = {
            "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
            "Pb": np.array([[0.0, 1.0, 2.0, 3.0], [1.0, 1.5, 2.5, 3.5]]),
            "I": np.array([[0.0, 4.0], [1.0, 5.0]]),
        }

        self.assertEqual(get_pdos_trace_options(dos_data), ["Total DOS", "Pb(s)", "Pb(p)", "I"])

    def test_plot_pdos_streamlit_respects_selected_trace_names(self) -> None:
        dos_data = {
            "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
            "Pb": np.array([[0.0, 1.0, 2.0, 3.0], [1.0, 1.5, 2.5, 3.5]]),
            "I": np.array([[0.0, 4.0], [1.0, 5.0]]),
        }

        fig = plot_pdos_streamlit(
            dos_data,
            shift=0.0,
            plot_range=(-1.0, 2.0),
            selected_trace_names=["Pb(p)", "I"],
        )

        self.assertEqual([trace.name for trace in fig.data], ["Pb(p)", "I"])

    def test_smooth_pdos_values_applies_centered_moving_average(self) -> None:
        smoothed = smooth_pdos_values(np.array([0.0, 0.0, 9.0, 0.0, 0.0]), 3)

        self.assertTrue(np.allclose(smoothed, np.array([0.0, 3.0, 3.0, 3.0, 0.0])))

    def test_plot_pdos_streamlit_applies_smoothing_and_width(self) -> None:
        dos_data = {
            "Total": np.array(
                [
                    [0.0, 0.0],
                    [1.0, 0.0],
                    [2.0, 9.0],
                    [3.0, 0.0],
                    [4.0, 0.0],
                ]
            ),
        }

        fig = plot_pdos_streamlit(
            dos_data,
            shift=0.0,
            plot_range=(0.0, 4.0),
            figure_width=640,
            smoothing_window=3,
        )

        self.assertTrue(np.allclose(fig.data[0].x, np.array([0.0, 3.0, 3.0, 3.0, 0.0])))
        self.assertEqual(fig.layout.width, 640)

    def test_plot_pdos_streamlit_applies_trace_colors(self) -> None:
        dos_data = {
            "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
            "I": np.array([[0.0, 4.0], [1.0, 5.0]]),
        }

        fig = plot_pdos_streamlit(
            dos_data,
            shift=0.0,
            plot_range=(-1.0, 2.0),
            trace_colors={"Total DOS": "#111111", "I": "#22aa66"},
        )

        self.assertEqual(fig.data[0].line.color, "#111111")
        self.assertEqual(fig.data[1].line.color, "#22aa66")

    def test_get_pdos_combination_labels_reads_named_and_implicit_labels(self) -> None:
        labels = get_pdos_combination_labels("PbI = Pb(s) + I\nI - I(p)")

        self.assertEqual(labels, ["PbI", "Combination 2"])

    def test_add_pdos_combinations_evaluates_addition_and_subtraction(self) -> None:
        pdos_table = build_pdos_table(
            {
                "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
                "Pb": np.array([[0.0, 1.0, 2.0, 3.0], [1.0, 1.5, 2.5, 3.5]]),
                "I": np.array([[0.0, 4.0, 0.5, 1.25], [1.0, 5.0, 0.75, 1.5]]),
            }
        )

        table, combination_columns = add_pdos_combinations(
            pdos_table,
            "PbI = Pb(s) + Pb(p) + I\nI without p = I - I(p)",
        )

        self.assertEqual(combination_columns, ["PbI", "I without p"])
        self.assertTrue(np.allclose(table["PbI"], np.array([9.0, 11.0])))
        self.assertTrue(np.allclose(table["I without p"], np.array([2.75, 3.5])))

    def test_add_pdos_combinations_rejects_unknown_terms(self) -> None:
        table = build_pdos_table(
            {
                "Total": np.array([[0.0, 10.0]]),
                "I": np.array([[0.0, 4.0]]),
            }
        )

        with self.assertRaisesRegex(ValueError, "not an available PDOS contribution"):
            add_pdos_combinations(table, "Bad = I - I(p)")

    def test_add_pdos_combination_traces_appends_custom_traces(self) -> None:
        table = build_pdos_table(
            {
                "Total": np.array([[0.0, 10.0], [1.0, 11.0]]),
                "I": np.array([[0.0, 4.0, 0.5, 1.25], [1.0, 5.0, 0.75, 1.5]]),
            }
        )
        table, combination_columns = add_pdos_combinations(table, "I without p = I - I(p)")
        fig = plot_pdos_streamlit(
            {"Total": np.array([[0.0, 10.0], [1.0, 11.0]]), "I": table[["Energy", "I"]].to_numpy()},
            shift=0.25,
            plot_range=(-1.0, 2.0),
        )

        add_pdos_combination_traces(
            fig,
            table,
            combination_columns,
            shift=0.25,
            trace_colors={"I without p": "#123abc"},
            smoothing_window=3,
        )

        self.assertEqual(fig.data[-1].name, "I without p")
        self.assertEqual(fig.data[-1].line.color, "#123abc")
        self.assertEqual(len(fig.data[-1].x), 2)
        self.assertTrue(np.allclose(fig.data[-1].y, np.array([0.25, 1.25])))

    def test_get_rec_vector_supports_geometry_in_style_lattice_lines(self) -> None:
        geometry = io.StringIO(
            "\n".join(
                [
                    "lattice 1.0 0.0 0.0",
                    "lattice 0.0 1.0 0.0",
                    "lattice 0.0 0.0 1.0",
                ]
            )
        )

        reciprocal = get_rec_vector(geometry)

        self.assertTrue(np.allclose(reciprocal, 2 * np.pi * np.eye(3)))

    def test_prepare_plot_data_applies_reciprocal_lattice_scaling(self) -> None:
        spin_texture = io.StringIO(
            "\n".join(
                [
                    "1 0.5 0.0 0.0 7 -1.25 0.1 0.2 0.3 0.5 0.0 0.0",
                    "2 0.0 0.5 0.0 7 -1.10 0.4 0.5 0.6 0.0 0.5 0.0",
                ]
            )
        )
        geometry = io.StringIO(
            "\n".join(
                [
                    "lattice_vector 2.0 0.0 0.0",
                    "lattice_vector 0.0 2.0 0.0",
                    "lattice_vector 0.0 0.0 2.0",
                ]
            )
        )

        k_points, spins, energy = prepare_plot_data(spin_texture, 7, geometry_file=geometry)

        expected_k_points = np.array(
            [
                [np.pi / 2, 0.0, 0.0],
                [0.0, np.pi / 2, 0.0],
            ]
        )
        self.assertTrue(np.allclose(k_points, expected_k_points))
        self.assertTrue(np.allclose(spins, np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])))
        self.assertTrue(np.allclose(energy, np.array([-1.25, -1.10])))

    def test_resolve_spin_texture_plane_matches_xy_2d_mapping(self) -> None:
        k_points = np.array([[1.0, 2.0, 3.0]])
        spins = np.array([[0.1, 0.2, 0.3]])

        k1, k2, spin_1, spin_2, color_component, ax_label_1, ax_label_2 = resolve_spin_texture_plane(
            k_points, spins, "z", "xy"
        )

        self.assertTrue(np.allclose(k1, np.array([10.0])))
        self.assertTrue(np.allclose(k2, np.array([20.0])))
        self.assertTrue(np.allclose(spin_1, np.array([0.1])))
        self.assertTrue(np.allclose(spin_2, np.array([0.2])))
        self.assertTrue(np.allclose(color_component, np.array([0.3])))
        self.assertEqual(ax_label_1, "kx ($nm^{-1}$)")
        self.assertEqual(ax_label_2, "ky ($nm^{-1}$)")

    def test_resolve_spin_texture_plane_matches_yz_2d_mapping(self) -> None:
        k_points = np.array([[1.0, 2.0, 3.0]])
        spins = np.array([[0.1, 0.2, 0.3]])

        k1, k2, spin_1, spin_2, color_component, ax_label_1, ax_label_2 = resolve_spin_texture_plane(
            k_points, spins, "x", "yz"
        )

        self.assertTrue(np.allclose(k1, np.array([20.0])))
        self.assertTrue(np.allclose(k2, np.array([30.0])))
        self.assertTrue(np.allclose(spin_1, np.array([0.2])))
        self.assertTrue(np.allclose(spin_2, np.array([0.3])))
        self.assertTrue(np.allclose(color_component, np.array([0.1])))
        self.assertEqual(ax_label_1, "ky ($nm^{-1}$)")
        self.assertEqual(ax_label_2, "kz ($nm^{-1}$)")


if __name__ == "__main__":
    unittest.main()
