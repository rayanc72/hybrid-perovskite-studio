from __future__ import annotations

import unittest

from hps.ui.workspaces.structure.navigation import StructureSelection


class StructureWorkspaceNavigationTests(unittest.TestCase):
    def test_analysis_selection_maps_to_one_workflow(self) -> None:
        selection = StructureSelection(
            mode="Analysis",
            group="PXRD Analysis",
            tool="Simulate PXRD",
        )
        self.assertTrue(selection.pxrd)
        self.assertFalse(selection.pdf)
        self.assertFalse(selection.rotation)

    def test_transformation_selection_is_mode_scoped(self) -> None:
        selection = StructureSelection(
            mode="Transformations",
            group="Molecule Operations",
            tool="Rotation",
        )
        self.assertTrue(selection.rotation)
        self.assertFalse(selection.symmetry)
        self.assertFalse(selection.translation)

    def test_tool_properties_preserve_existing_labels(self) -> None:
        self.assertTrue(
            StructureSelection("Analysis", "Symmetry", "Symmetrize structure").symmetry
        )
        self.assertTrue(
            StructureSelection(
                "Analysis",
                "Structure Metrics",
                "Anisotropic displacement parameters",
            ).adp_table
        )
