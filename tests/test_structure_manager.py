from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from ase import Atoms
    from hps.domain import structure_manager
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    structure_manager = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(structure_manager is None, f"Optional test dependency unavailable: {_IMPORT_ERROR}")
class StructureManagerLabelTests(unittest.TestCase):
    def test_build_molecule_label_overrides_applies_symbol_prefix(self) -> None:
        atoms = Atoms(symbols=["Pb", "I", "I", "I"], positions=[[0, 0, 0]] * 4)

        overrides = structure_manager.build_molecule_label_overrides(atoms, [0, 1, 2, 3], "l1")

        self.assertEqual(
            overrides,
            {
                0: "Pbl1",
                1: "Il1",
                2: "Il1",
                3: "Il1",
            },
        )

    def test_write_modified_aims_file_uses_custom_overrides_for_selected_atoms(self) -> None:
        atoms = Atoms(symbols=["Pb", "I", "Cs"], positions=[[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        buffer = io.StringIO()

        structure_manager.write_modified_aims_file(
            atoms,
            buffer,
            atom_label_overrides={0: "Pbl1", 1: "Il1"},
        )

        output = buffer.getvalue()
        self.assertIn("atom 0.0 0.0 0.0 Pbl1", output)
        self.assertIn("atom 1.0 0.0 0.0 Il1", output)
        self.assertIn("atom 2.0 0.0 0.0 Cs3", output)

    def test_render_labelled_geometry_content_preserves_existing_geometry_lines(self) -> None:
        atoms = Atoms(symbols=["Pb", "Pb", "I"], positions=[[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        original_content = (
            "lattice_vector     28.17499353      0.00000000      0.00000000\n"
            "atom      21.13114261      6.90882199      1.35016097 Pb\n"
            "atom       7.04395647      2.30304094      1.35014681 Pb\n"
            "atom      17.99510339      7.53686848      1.47344446 I\n"
        )

        output = structure_manager.render_labelled_geometry_content(
            atoms,
            atom_label_overrides={0: "Pbl1", 2: "Il1"},
            original_content=original_content,
        )

        self.assertIn("lattice_vector     28.17499353      0.00000000      0.00000000", output)
        self.assertIn("atom      21.13114261      6.90882199      1.35016097 Pbl1", output)
        self.assertIn("atom       7.04395647      2.30304094      1.35014681 Pb", output)
        self.assertIn("atom      17.99510339      7.53686848      1.47344446 Il1", output)

    def test_render_labelled_geometry_content_keeps_unselected_atoms_as_plain_symbols(self) -> None:
        atoms = Atoms(symbols=["Pb", "I", "Cs"], positions=[[0, 0, 0], [1, 0, 0], [2, 0, 0]])

        output = structure_manager.render_labelled_geometry_content(
            atoms,
            atom_label_overrides={0: "Pbl1"},
        )

        self.assertIn("atom 0.0 0.0 0.0 Pbl1", output)
        self.assertIn("atom 1.0 0.0 0.0 I", output)
        self.assertIn("atom 2.0 0.0 0.0 Cs", output)

    def test_build_molecule_label_overrides_rejects_invalid_label_characters(self) -> None:
        atoms = Atoms(symbols=["Pb"], positions=[[0, 0, 0]])

        with self.assertRaises(ValueError):
            structure_manager.build_molecule_label_overrides(atoms, [0], "l 1")

    def test_multiple_molecule_label_overrides_can_be_merged(self) -> None:
        atoms = Atoms(symbols=["Pb", "I", "Pb", "I"], positions=[[0, 0, 0]] * 4)

        first = structure_manager.build_molecule_label_overrides(atoms, [0, 1], "l1")
        second = structure_manager.build_molecule_label_overrides(atoms, [2, 3], "l2")

        merged = {}
        merged.update(first)
        merged.update(second)

        self.assertEqual(
            merged,
            {
                0: "Pbl1",
                1: "Il1",
                2: "Pbl2",
                3: "Il2",
            },
        )


if __name__ == "__main__":
    unittest.main()
