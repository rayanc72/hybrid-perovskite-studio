"""Runtime helpers for discovering and launching the local backend service."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from hps.io.paths import APP_BACKEND_LOG, ensure_runtime_dirs

DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8765


def backend_base_url() -> str:
    return os.environ.get("HPS_BACKEND_URL", f"http://{DEFAULT_BACKEND_HOST}:{DEFAULT_BACKEND_PORT}")


def _health_url() -> str:
    return f"{backend_base_url().rstrip('/')}/health"


def backend_is_healthy(timeout: float = 0.5) -> bool:
    try:
        with urlopen(_health_url(), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok"
    except (OSError, URLError, TimeoutError, ValueError):
        return False


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def ensure_local_backend_running(startup_timeout: float = 5.0) -> str:
    ensure_runtime_dirs()
    if backend_is_healthy():
        return backend_base_url()

    host = os.environ.get("HPS_BACKEND_HOST", DEFAULT_BACKEND_HOST)
    port = int(os.environ.get("HPS_BACKEND_PORT", str(DEFAULT_BACKEND_PORT)))
    if not _port_is_open(host, port):
        with APP_BACKEND_LOG.open("a", encoding="utf-8") as log_file:
            subprocess.Popen(
                [sys.executable, "-m", "hps.api.server", "--host", host, "--port", str(port)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    deadline = time.time() + startup_timeout
    while time.time() < deadline:
        if backend_is_healthy():
            os.environ["HPS_BACKEND_URL"] = f"http://{host}:{port}"
            return backend_base_url()
        time.sleep(0.2)

    raise RuntimeError("Local backend failed to become ready.")
