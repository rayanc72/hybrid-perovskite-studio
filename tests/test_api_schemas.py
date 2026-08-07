from __future__ import annotations

import base64
import unittest

from pydantic import ValidationError

from hps.api.schemas import (
    NamedContentFile,
    StructurePxrdRequest,
    StructureSymmetryRequest,
)


class ApiSchemaTests(unittest.TestCase):
    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaises(ValidationError):
            NamedContentFile(name="input.dat", content_b64="not base64!")

    def test_rejects_invalid_pxrd_ranges(self) -> None:
        encoded = base64.b64encode(b"structure").decode("ascii")
        with self.assertRaises(ValidationError):
            StructurePxrdRequest(
                file_name="demo.cif",
                file_bytes_b64=encoded,
                two_theta_range=(80.0, 5.0),
            )
        with self.assertRaises(ValidationError):
            StructurePxrdRequest(
                file_name="demo.cif",
                file_bytes_b64=encoded,
                num_points=1_000_000,
            )

    def test_rejects_reversed_symmetry_tolerances(self) -> None:
        encoded = base64.b64encode(b"structure").decode("ascii")
        with self.assertRaises(ValidationError):
            StructureSymmetryRequest(
                file_name="demo.cif",
                file_bytes_b64=encoded,
                symprec_lower=1.0,
                symprec_upper=0.1,
                angle_tol=5.0,
            )
