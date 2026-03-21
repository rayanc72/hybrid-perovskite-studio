from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np

try:
    from pymatgen.core import Lattice
    from pymatgen.core.structure import Structure
    from hps.domain import molecule_builder
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    molecule_builder = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(molecule_builder is None, f"Optional test dependency unavailable: {_IMPORT_ERROR}")
class MoleculeBuilderTests(unittest.TestCase):
    def test_create_distance_matrix_is_symmetric(self) -> None:
        coords = np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]])
        df = molecule_builder.create_distance_matrix(coords)
        self.assertEqual(df.shape, (2, 2))
        self.assertEqual(df.iloc[0, 0], 0.0)
        self.assertAlmostEqual(df.iloc[0, 1], 5.0)
        self.assertAlmostEqual(df.iloc[1, 0], 5.0)

    def test_get_connected_coordinates_returns_initial_coords_when_already_connected(self) -> None:
        lattice = Lattice.cubic(10)
        structure = Structure(
            lattice,
            ["H", "H"],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.074]],
            coords_are_cartesian=True,
        )
        result = molecule_builder.get_connected_coordinates(structure, max_iterations=0)
        self.assertIsNotNone(result)
        self.assertTrue(np.allclose(result, structure.cart_coords))

    def test_get_connected_coordinates_rejects_negative_iterations(self) -> None:
        lattice = Lattice.cubic(10)
        structure = Structure(
            lattice,
            ["H", "H"],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.074]],
            coords_are_cartesian=True,
        )
        with self.assertRaises(ValueError):
            molecule_builder.get_connected_coordinates(structure, max_iterations=-1)

    def test_get_molecule_object_raises_when_connectivity_cannot_be_resolved(self) -> None:
        class DummyAtoms:
            def __getitem__(self, item):
                return item

        original = molecule_builder.AseAtomsAdaptor
        original_get_connected = molecule_builder.get_connected_coordinates

        class FakeAdaptor:
            def get_structure(self, _molecule_atoms):
                lattice = Lattice.cubic(10)
                return Structure(
                    lattice,
                    ["H", "H"],
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.074]],
                    coords_are_cartesian=True,
                )

        try:
            molecule_builder.AseAtomsAdaptor = lambda: FakeAdaptor()
            molecule_builder.get_connected_coordinates = lambda *_args, **_kwargs: None
            with self.assertRaises(ValueError):
                molecule_builder.get_molecule_object(DummyAtoms(), [0, 1])
        finally:
            molecule_builder.AseAtomsAdaptor = original
            molecule_builder.get_connected_coordinates = original_get_connected


if __name__ == "__main__":
    unittest.main()
