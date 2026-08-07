from __future__ import annotations

import time
from concurrent.futures import Future
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from hps.services.backend_jobs import WORKFLOW_REGISTRY, BackendJobManager
from hps.services.backend_store import BackendStore


class InlineExecutor:
    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as exc:  # pragma: no cover - mirrors Executor behavior
            future.set_exception(exc)
        return future


def test_cached_submission_reuses_profiled_result_with_lower_latency() -> None:
    calls = 0

    def measured_workflow(payload: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        return {"value": payload["value"]}

    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        store = BackendStore(root / "jobs.sqlite3", root / "artifacts")
        manager = BackendJobManager(store=store, executor=InlineExecutor())
        with patch.dict(WORKFLOW_REGISTRY, {"structure_summary": measured_workflow}):
            cold_started = time.perf_counter()
            cold = manager.submit("structure_summary", {"value": 42})
            cold_latency = time.perf_counter() - cold_started

            cached_started = time.perf_counter()
            cached = manager.submit("structure_summary", {"value": 42})
            cached_latency = time.perf_counter() - cached_started

    assert cold["state"] == "completed"
    assert cold["execution_duration_ms"] >= 20.0
    assert cached["job_id"] == cold["job_id"]
    assert cached["cache_hit"] is True
    assert cached["cache_hit_count"] == 1
    assert calls == 1
    assert cached_latency < cold_latency
