from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest


BACKEND_HEALTH = {
    "status": "ok",
    "service": "hps-backend",
    "version": "test",
    "base_url": "http://127.0.0.1:8765",
}


def test_packaged_app_opens_dynamics_trajectory_view() -> None:
    with patch(
        "hps.services.backend_runtime.validate_backend_connection",
        return_value=BACKEND_HEALTH,
    ):
        app = AppTest.from_file("src/hps/app.py", default_timeout=30).run()
        assert not app.exception
        assert {button.label for button in app.button} >= {
            "Open Structure",
            "Open Electronic",
            "Open Dynamics",
            "Open Utilities",
        }

        next(button for button in app.button if button.label == "Open Dynamics").click().run()
        assert not app.exception
        assert app.radio[0].options == ["Analyze AIMS MD output", "Trajectory analysis"]

        app.radio[0].set_value("Trajectory analysis").run()
        assert not app.exception
        assert [item.label for item in app.number_input] == ["Enter timestep in fs (dt)"]
        assert [item.label for item in app.file_uploader] == ["Upload zipped directory"]
