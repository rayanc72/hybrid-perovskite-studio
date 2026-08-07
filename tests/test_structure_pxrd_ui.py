from __future__ import annotations

import unittest

import numpy as np

from hps.ui.workspaces.structure.analysis.pxrd import (
    build_pxrd_payload,
    normalize_comparison_profiles,
    parse_experimental_pxrd,
    requested_two_theta_range,
    x_values_to_d_spacing,
)


class StructurePxrdUiTests(unittest.TestCase):
    def test_q_range_converts_to_two_theta(self) -> None:
        converted = requested_two_theta_range("q", 1.0, 2.0, 1.5406)
        self.assertLess(converted[0], converted[1])
        self.assertGreater(converted[0], 0.0)

    def test_invalid_ranges_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            requested_two_theta_range("2theta", 20.0, 10.0, 1.5406)
        with self.assertRaises(ValueError):
            requested_two_theta_range("q", 0.0, 1.0, 1.5406)

    def test_experimental_parser_converts_and_clips_data(self) -> None:
        frame = parse_experimental_pxrd(
            b"# header\n10 2\n20 4\n90 8\n",
            source_axis="2theta",
            target_axis="2theta",
            wavelength=1.5406,
            x_column="2theta (deg)",
            simulated_range=(5.0, 30.0),
        )
        self.assertEqual(frame["2theta (deg)"].tolist(), [10, 20])

    def test_comparison_normalization_uses_independent_maxima(self) -> None:
        simulated, experimental, reflections = normalize_comparison_profiles(
            [0.0, 10.0], [0.0, 5.0], [5.0]
        )
        self.assertTrue(np.allclose(simulated, [0.0, 1.0]))
        self.assertTrue(np.allclose(experimental, [0.0, 1.0]))
        self.assertTrue(np.allclose(reflections, [0.5]))

    def test_payload_encodes_structure_without_symmetry_fields(self) -> None:
        payload = build_pxrd_payload(
            "sample.cif",
            b"structure",
            wavelength=1.5406,
            two_theta_range=(5.0, 50.0),
            fwhm=0.1,
            x_axis="2theta",
        )
        self.assertEqual(payload["file_name"], "sample.cif")
        self.assertEqual(payload["two_theta_range"], [5.0, 50.0])
        self.assertNotIn("symprec_lower", payload)

    def test_q_result_label_is_used_for_d_spacing(self) -> None:
        self.assertTrue(
            np.allclose(x_values_to_d_spacing([2.0], "q (A^-1)", 1.5406), [np.pi])
        )
