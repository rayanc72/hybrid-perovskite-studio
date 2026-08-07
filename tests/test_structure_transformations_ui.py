from __future__ import annotations

import unittest

from hps.ui.workspaces.structure.transformations.operations import (
    TRANSLATION_AXES,
    parse_atom_indices,
    structure_file_root,
)
from hps.ui.workspaces.structure.transformations.rotation import ROTATION_TYPES


class StructureTransformationsUiTests(unittest.TestCase):
    def test_output_root_handles_missing_and_compound_names(self) -> None:
        self.assertEqual(structure_file_root(None), "structure")
        self.assertEqual(structure_file_root("sample.relaxed.cif"), "sample.relaxed")

    def test_atom_index_parser_accepts_commas_and_whitespace(self) -> None:
        self.assertEqual(parse_atom_indices("1, 2  5\n8"), [1, 2, 5, 8])
        with self.assertRaises(ValueError):
            parse_atom_indices("1, two")

    def test_transformation_option_registries_are_complete(self) -> None:
        self.assertEqual(
            ROTATION_TYPES,
            (
                "Rotate Individual Molecules",
                "Rotate Multiple Molecules",
                "Random Rotation",
                "Interpolate by Rotation",
                "Rotate Part of Molecules",
                "Rotate by Dipole Moment",
            ),
        )
        self.assertIn("custom", TRANSLATION_AXES)
        self.assertIn("xyz", TRANSLATION_AXES)


if __name__ == "__main__":
    unittest.main()
