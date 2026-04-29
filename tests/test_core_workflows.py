from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from hps.core.electronic import parse_pdos_payload
    from hps.core.md import parse_md_outputs
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    parse_pdos_payload = None
    parse_md_outputs = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(parse_pdos_payload is None or parse_md_outputs is None, f"Optional test dependency unavailable: {_IMPORT_ERROR}")
class CoreWorkflowTests(unittest.TestCase):
    def test_parse_pdos_payload_returns_roles_table_and_combinations(self) -> None:
        total = b"-2 1\n0 2\n2 1\n"
        pb = b"-2 0 1 2\n0 0 2 3\n2 0 1 1\n"
        iodine = b"-2 4\n0 5\n2 4\n"

        result = parse_pdos_payload(
            [
                {"name": "KS_DOS_total.dat", "content": total},
                {"name": "Pb_l_proj_dos.dat", "content": pb},
                {"name": "I_l_proj_dos.dat", "content": iodine},
            ],
            combination_text="PbI = Pb(s) + Pb(p) + I",
        )

        self.assertEqual(result["roles"]["total"], ["KS_DOS_total.dat"])
        self.assertEqual(len(result["roles"]["projected"]), 2)
        self.assertIn("Total DOS", result["trace_options"])
        self.assertIn("PbI", result["pdos_columns"])
        self.assertEqual(len(result["pdos_table"]), 3)

    def test_parse_md_outputs_returns_table(self) -> None:
        md_content = (
            b"Initial conditions for Born-Oppenheimer Molecular Dynamics:\n"
            b"ignored line\n"
            b"Time: 0.0 ps\n"
            b"E_tot: -100.0 eV\n"
            b"Temperature: 300 K\n"
            b"E_kin: 1.0 eV\n"
            b"Total Energy: -99.0 eV\n"
            b"Conserved Hamiltonian: -98.5 eV\n"
            b"Advancing structure using Born-Oppenheimer Molecular Dynamics\n"
            b"ignored line\n"
            b"ignored line\n"
            b"Time: 1.0 ps\n"
            b"E_tot: -100.5 eV\n"
            b"Temperature: 310 K\n"
            b"E_kin: 1.1 eV\n"
            b"Total Energy: -99.4 eV\n"
            b"Conserved Hamiltonian: -98.8 eV\n"
        )

        result = parse_md_outputs([{"name": "md1.out", "content": md_content}])
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["columns"][0], "Time [ps]")


if __name__ == "__main__":
    unittest.main()
