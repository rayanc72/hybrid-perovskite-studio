from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

BACKEND_HEALTH = {
    "status": "ok",
    "service": "hps-backend",
    "version": "test",
    "base_url": "http://127.0.0.1:8765",
}
APP_PATH = Path(__file__).resolve().parents[1] / "src" / "hps" / "app.py"


def test_packaged_app_opens_dynamics_trajectory_view() -> None:
    with patch(
        "hps.services.backend_runtime.validate_backend_connection",
        return_value=BACKEND_HEALTH,
    ):
        app = AppTest.from_file(APP_PATH, default_timeout=30)
        app.query_params["workspace"] = "Dynamics"
        app.run()
        assert not app.exception
        assert app.radio[0].options == ["Analyze AIMS MD output", "Trajectory analysis"]

        app.radio[0].set_value("Trajectory analysis").run()
        assert not app.exception
        assert [item.label for item in app.number_input] == ["Enter timestep in fs (dt)"]
        assert [item.label for item in app.file_uploader] == ["Upload zipped directory"]


def test_structure_workspace_opens_without_a_tool_and_keeps_cif_details_visible() -> None:
    cif = b'''data_demo
_cell_length_a 1.5
_cell_length_b 12
_cell_length_c 12
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
C1 C 0 0 0
He2 He 0 0.3333333333333333 0
'''
    with (
        patch(
            "hps.services.backend_runtime.validate_backend_connection",
            return_value=BACKEND_HEALTH,
        ),
        patch("hps.ui.workspaces.structure.overview.prime_summary_job"),
        patch("hps.ui.workspaces.structure.overview.refresh_summary_status"),
    ):
        app = AppTest.from_file(APP_PATH, default_timeout=30)
        app.query_params["workspace"] = "Structure"
        app.run()
        assert not app.exception
        assert len(app.radio) == 1
        assert app.radio[0].options == ["Analysis", "Transformations"]
        assert app.radio[0].value is None
        assert not app.selectbox
        assert not app.warning

        app.session_state["uploaded_structure_name"] = "demo.cif"
        app.session_state["uploaded_structure_bytes"] = cif
        app.session_state["file_name"] = "demo.cif"
        app.run()
        assert not app.exception
        assert app.radio[0].value is None
        assert app.metric[0].value == "demo.cif"
        assert "Molecule groups and names" in [item.label for item in app.expander]
        text = "\n".join(item.value for item in app.markdown)
        assert "Group 1 (1D periodic network): C1" in text
        assert "Group 2 (finite molecule): He2" in text
        nodes = list(app.main)
        upload = next(i for i, node in enumerate(nodes) if node.type == "file_uploader")
        summary = next(
            i for i, node in enumerate(nodes)
            if node.type == "markdown" and node.value == "### Current Structure"
        )
        view = next(i for i, node in enumerate(nodes) if node.type == "radio")
        assert upload < summary < view

        for mode in ("Analysis", "Transformations"):
            app.radio[0].set_value(mode).run()
            assert not app.exception
            assert app.metric[0].value == "demo.cif"
            assert "Molecule groups and names" in [item.label for item in app.expander]
