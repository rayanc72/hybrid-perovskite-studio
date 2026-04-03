from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.domain.electronic_property import (
    get_rec_vector,
    prepare_plot_data,
    resolve_spin_texture_plane,
)


class ElectronicPropertyTests(unittest.TestCase):
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
