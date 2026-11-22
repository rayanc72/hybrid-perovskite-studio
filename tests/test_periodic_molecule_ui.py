"""The UI retains group numbers while separating molecules from networks."""

from streamlit.testing.v1 import AppTest


def test_structure_details_rotation_and_com_distinguish_periodic_groups():
    app = AppTest.from_string(
        '''
import streamlit as st
from ase import Atoms
from ase.spacegroup import Spacegroup
from hps.core.molecules import detect_molecules
from hps.ui.workspaces.structure.overview import _render_structure_details
from hps.ui.workspaces.structure.transformations.rotation import render_rotation
from hps.ui.workspaces.structure.analysis.molecules import render_molecule_analysis

atoms = Atoms("CHe", positions=[[0, 0, 0], [0, 4, 0]],
              cell=[1.5, 12, 12], pbc=[True, False, False])
atoms.info["spacegroup"] = Spacegroup(1)
groups = detect_molecules(atoms)
header = lambda title, **kwargs: st.subheader(title)
_render_structure_details(atoms, groups, ["C1", "He2"])
render_rotation(atoms, groups, "test.in", render_section_header=header)
render_molecule_analysis(
    polarization_option=False, charge_analysis_option=False, com_option=True,
    dm_option=False, modified_atoms=atoms, molecules=groups,
    render_section_header=header,
)
''',
        default_timeout=30,
    ).run()
    assert not app.exception
    details = "\n".join(item.value for item in app.markdown)
    assert "Group 1 (1D periodic network)" in details
    assert "Group 2 (finite molecule)" in details
    assert app.multiselect[0].options == ["2"]
    assert list(app.dataframe[0].value.index) == ["Molecule 2", "Unit Cell Center"]


def test_structure_details_cache_refreshes_for_geometry_and_bond_settings():
    app = AppTest.from_string(
        '''
import streamlit as st
from ase import Atoms
from hps.core.molecules import BOND_SETTINGS_KEY
from hps.ui.workspaces.structure.overview import _render_structure_details

atoms = Atoms("CHe", positions=[[0, 0, 0], [0, 4, 0]],
              cell=[1.5, 12, 12], pbc=[True, False, False])
change = st.radio("Structure change", ["None", "Cell", "Periodicity", "Bond settings"])
if change == "Cell":
    atoms.set_cell([12, 12, 12])
elif change == "Periodicity":
    atoms.pbc = False
elif change == "Bond settings":
    atoms.info[BOND_SETTINGS_KEY] = {"exceptions": [("C", "C")]}
_render_structure_details(atoms, [[0], [1]], ["C1", "He2"])
''',
        default_timeout=30,
    ).run()
    assert not app.exception
    assert "Group 1 (1D periodic network)" in "\n".join(item.value for item in app.markdown)
    for change in ("Cell", "Periodicity", "Bond settings"):
        app.radio[0].set_value(change).run()
        assert not app.exception
        assert "Group 1 (finite molecule)" in "\n".join(item.value for item in app.markdown)
