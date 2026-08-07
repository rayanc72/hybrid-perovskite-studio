from __future__ import annotations

import unittest

from hps.ui.workspaces.structure.analysis.charge import (
    parse_bader_integrated_atomic_properties,
    parse_id_field,
)


class StructureChargeUiTests(unittest.TestCase):
    def test_id_parser_supports_ranges_order_and_deduplication(self) -> None:
        self.assertEqual(parse_id_field("1, 3:5, 4, 8:7, bad"), [1, 3, 4, 5, 8, 7])

    def test_bader_parser_computes_partial_charge(self) -> None:
        frame = parse_bader_integrated_atomic_properties(
            """* Integrated atomic properties
Id cp ncp Name Z mult Volume Pop Lap
1 0 0 I_ 53 1 10.0 52.25 0.0
2 0 0 Pb 82 1 12.0 80.5 0.0

"""
        )
        self.assertEqual(frame["Name"].tolist(), ["I", "Pb"])
        self.assertEqual(frame["PartialCharge"].tolist(), [0.75, 1.5])


if __name__ == "__main__":
    unittest.main()
