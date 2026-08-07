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
