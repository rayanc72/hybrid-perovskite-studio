from __future__ import annotations

import base64
import unittest

from hps.ui.workspaces.structure.analysis.symmetry import (
    build_symmetry_payload,
    symmetry_output_filename,
)


class StructureSymmetryUiTests(unittest.TestCase):
    def test_payload_serializes_structure_and_numeric_controls(self) -> None:
        payload = build_symmetry_payload("demo.cif", b"content", 0.001, 0.1, 5.0)
        self.assertEqual(payload["file_name"], "demo.cif")
        self.assertEqual(base64.b64decode(payload["file_bytes_b64"]), b"content")
        self.assertEqual(payload["symprec_lower"], 0.001)
        self.assertEqual(payload["symprec_upper"], 0.1)
        self.assertEqual(payload["angle_tol"], 5.0)

    def test_output_filename_uses_active_structure_root(self) -> None:
        self.assertEqual(symmetry_output_filename("sample.geometry.cif"), "sample.geometry_high_symm.cif")
        self.assertEqual(symmetry_output_filename(None), "structure_high_symm.cif")
