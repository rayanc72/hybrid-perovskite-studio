from __future__ import annotations

import ast
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hps.services.runtime import DEPENDENCY_GROUPS, full_install_command, pdf_install_command
from hps.ui.navigation import tool_options
from hps.ui.sidebar import SIDEBAR_SECTIONS


class PackageLayoutTests(unittest.TestCase):
    def test_expected_directories_exist(self) -> None:
        expected = [
            ROOT / "src" / "hps" / "domain",
            ROOT / "src" / "hps" / "io",
            ROOT / "src" / "hps" / "services",
            ROOT / "src" / "hps" / "ui",
            ROOT / "docs",
            ROOT / "tests",
        ]
        for path in expected:
            self.assertTrue(path.exists(), f"Missing expected path: {path}")

    def test_required_dependency_groups_exist(self) -> None:
        names = {group.name for group in DEPENDENCY_GROUPS}
        self.assertTrue({"core", "md", "pdf", "viz", "auth"}.issubset(names))
        self.assertEqual(full_install_command(), "pip install -e '.[full]'")
        self.assertEqual(pdf_install_command(), "pip install -e '.[pdf]'")

    def test_sidebar_catalog_is_not_empty(self) -> None:
        titles = {section.title for section in SIDEBAR_SECTIONS}
        self.assertIn("Structure Analysis", titles)
        self.assertIn("Electronic Analysis", titles)
        self.assertGreaterEqual(sum(len(section.items) for section in SIDEBAR_SECTIONS), 10)

    def test_pyproject_has_expected_extras(self) -> None:
        data = tomllib.loads((ROOT / "pyproject.toml").read_text())
        extras = data["project"]["optional-dependencies"]
        for extra in ("core", "md", "pdf", "viz", "auth", "full", "dev"):
            self.assertIn(extra, extras)

    def test_requirements_uses_editable_package_install(self) -> None:
        requirements = (ROOT / "requirements.txt").read_text().strip()
        self.assertEqual(requirements, "-e .[full,dev]")

    def test_no_star_imports_in_packaged_code(self) -> None:
        for path in (ROOT / "src" / "hps").rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported_names = {alias.name for alias in node.names}
                    self.assertNotIn("*", imported_names, f"Wildcard import found in {path}")

    def test_packaged_entrypoint_uses_packaged_app_module(self) -> None:
        entrypoint = (ROOT / "src" / "hps" / "app.py").read_text()
        self.assertIn('module_name = "hps.ui.app_main"', entrypoint)
        self.assertIn("importlib.reload(sys.modules[module_name])", entrypoint)
        self.assertIn("importlib.import_module(module_name)", entrypoint)

    def test_packaged_pdf_wrapper_uses_packaged_module(self) -> None:
        wrapper = (ROOT / "src" / "hps" / "domain" / "pdf.py").read_text()
        self.assertIn("from hps.domain import pdf_analysis as _impl", wrapper)

    def test_pdf_analysis_workflows_are_separate_tools(self) -> None:
        self.assertEqual(
            tool_options("Structure", "Analysis", "PDF Analysis"),
            [
                "Simulate PDF",
                "Plot RDF",
                "Compare experimental PDF",
                "Convert reduced PDF to g(r)",
            ],
        )

    def test_pdf_analysis_exports_diffpy_structure_loader(self) -> None:
        pdf_analysis = (ROOT / "src" / "hps" / "domain" / "pdf_analysis.py").read_text()
        self.assertIn("from diffpy.structure import loadStructure", pdf_analysis)

    def test_plot_band_is_import_safe(self) -> None:
        plot_band = (ROOT / "src" / "hps" / "tools" / "plot_band.py").read_text()
        self.assertIn('if __name__ == "__main__":', plot_band)
        self.assertNotIn("ymax = float(sys.argv[3])", plot_band)


if __name__ == "__main__":
    unittest.main()
