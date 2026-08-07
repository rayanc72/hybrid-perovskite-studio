from __future__ import annotations

import unittest

from hps.ui.workspaces.structure.analysis.pdf import (
    PDF_WORKFLOW_TITLES,
    parse_reduced_pdf,
)


class StructurePdfUiTests(unittest.TestCase):
    def test_all_registered_workflows_have_titles(self) -> None:
        self.assertEqual(
            set(PDF_WORKFLOW_TITLES),
            {
                "Simulate PDF",
                "Plot RDF",
                "Compare experimental PDF",
                "Convert reduced PDF to g(r)",
            },
        )

    def test_reduced_pdf_parser_clips_and_coerces_data(self) -> None:
        frame = parse_reduced_pdf(
            b"header\n#### start data\nmeta\nmeta\n0.5 2\n1.0 4\nbad row\n3.0 8\n",
            (0.75, 2.0),
        )
        self.assertEqual(frame["r"].tolist(), [1.0])
        self.assertEqual(frame["G_exp"].tolist(), [4.0])

    def test_reduced_pdf_parser_rejects_missing_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "start data"):
            parse_reduced_pdf(b"0.5 2\n", (0.0, 1.0))

    def test_reduced_pdf_parser_rejects_empty_selected_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "selected r range"):
            parse_reduced_pdf(
                b"#### start data\nmeta\nmeta\n3.0 8\n",
                (0.0, 1.0),
            )


if __name__ == "__main__":
    unittest.main()
