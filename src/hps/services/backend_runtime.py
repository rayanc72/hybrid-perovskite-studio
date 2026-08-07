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
    if configured_url := os.environ.get("HPS_BACKEND_URL"):
        return configured_url
    host = os.environ.get("HPS_BACKEND_HOST", DEFAULT_BACKEND_HOST)
    port = os.environ.get("HPS_BACKEND_PORT", str(DEFAULT_BACKEND_PORT))
    return f"http://{host}:{port}"


def _health_url() -> str:
    return f"{backend_base_url().rstrip('/')}/health"


def backend_health(timeout: float = 0.5) -> dict[str, object] | None:
    """Return a validated backend health payload, or ``None`` when unreachable."""

    try:
        with urlopen(_health_url(), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok" and payload.get("service") == "hps-backend":
                return payload
    except (OSError, URLError, TimeoutError, ValueError):
        pass
    return None


def backend_is_healthy(timeout: float = 0.5) -> bool:
    return backend_health(timeout=timeout) is not None


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

    raise RuntimeError(
        f"Local backend at {backend_base_url()} failed to become ready within "
        f"{startup_timeout:.1f} seconds. See {APP_BACKEND_LOG} for details."
    )


def validate_backend_connection(startup_timeout: float = 5.0) -> dict[str, object]:
    """Start the backend when needed and verify the service identity and version."""

    base_url = ensure_local_backend_running(startup_timeout=startup_timeout)
    payload = backend_health(timeout=1.0)
    if payload is None:
        raise RuntimeError(f"Backend readiness validation failed for {base_url}.")
    if not payload.get("version"):
        raise RuntimeError(f"Backend at {base_url} did not report an application version.")
    return {"base_url": base_url, **payload}
