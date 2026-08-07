from __future__ import annotations

import unittest
from types import SimpleNamespace

from hps.ui.workspaces.structure.analysis.metrics import (
    LATTICE_PARAMETER_KEYS,
    build_lattice_deviation_table,
    distortion_function_map,
)


class StructureMetricsUiTests(unittest.TestCase):
    def test_lattice_deviation_table_uses_percentage_change(self) -> None:
        initial = SimpleNamespace(
            a=10.0,
            b=20.0,
            c=30.0,
            alpha=90.0,
            beta=90.0,
            gamma=90.0,
            volume=6000.0,
        )
        final = SimpleNamespace(
            a=11.0,
            b=18.0,
            c=30.0,
            alpha=99.0,
            beta=90.0,
            gamma=81.0,
            volume=5940.0,
        )
        table = build_lattice_deviation_table(initial, final)
        self.assertEqual(len(table), len(LATTICE_PARAMETER_KEYS))
        self.assertEqual(
            table["Deviation (%)"].round(6).tolist(),
            [10.0, -10.0, 0.0, 10.0, 0.0, -10.0, -1.0],
        )

    def test_distortion_registry_contains_selectable_calculations(self) -> None:
        names = set(distortion_function_map())
        self.assertTrue(
            {
                "Bond distance variance",
                "Angle variance",
                "Bridging angle(s)",
                "In and out deviations",
            }.issubset(names)
        )
        self.assertTrue(all(callable(function) for function in distortion_function_map().values()))


if __name__ == "__main__":
    unittest.main()
