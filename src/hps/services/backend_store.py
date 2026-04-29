"""SQLite-backed job and artifact persistence for the local backend."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import closing
from pathlib import Path

from hps.io.paths import APP_BACKEND_ARTIFACTS_DIR, APP_BACKEND_DB, ensure_runtime_dirs


class BackendStore:
    """Small persistent store for background jobs and derived artifacts."""

    def __init__(self, db_path: Path | None = None, artifact_dir: Path | None = None) -> None:
        ensure_runtime_dirs()
        self._db_path = Path(db_path or APP_BACKEND_DB)
        self._artifact_dir = Path(artifact_dir or APP_BACKEND_ARTIFACTS_DIR)
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    workflow TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL,
                    messages_json TEXT NOT NULL DEFAULT '[]',
                    result_ref TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_lookup
                    ON jobs (workflow, request_hash, state);

                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def create_job(self, *, workflow: str, request_hash: str, payload: dict[str, object]) -> str:
        job_id = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, workflow, request_hash, state, progress, payload_json)
                VALUES (?, ?, ?, 'queued', 0.0, ?)
                """,
                (job_id, workflow, request_hash, json.dumps(payload, sort_keys=True)),
            )
        return job_id

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row)

    def find_completed_job(self, *, workflow: str, request_hash: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE workflow = ? AND request_hash = ? AND state = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (workflow, request_hash),
            ).fetchone()
        return self._row_to_job(row)

    def update_job(
        self,
        job_id: str,
        *,
        state: str | None = None,
        progress: float | None = None,
        result_ref: str | None = None,
        error: str | None = None,
        append_message: str | None = None,
    ) -> None:
        with self._lock:
            job = self.get_job(job_id)
            if job is None:
                return
            messages = list(job["messages"])
            if append_message:
                messages.append(append_message)

            with closing(self._connect()) as conn, conn:
                conn.execute(
                    """
                    UPDATE jobs
                    SET state = COALESCE(?, state),
                        progress = COALESCE(?, progress),
                        result_ref = COALESCE(?, result_ref),
                        error = COALESCE(?, error),
                        messages_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (
                        state,
                        progress,
                        result_ref,
                        error,
                        json.dumps(messages),
                        job_id,
                    ),
                )

    def create_artifact(
        self,
        *,
        kind: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        suffix: str = ".bin",
    ) -> str:
        artifact_id = str(uuid.uuid4())
        artifact_path = self._artifact_dir / f"{artifact_id}{suffix}"
        artifact_path.write_bytes(data)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO artifacts (artifact_id, kind, content_type, path)
                VALUES (?, ?, ?, ?)
                """,
                (artifact_id, kind, content_type, str(artifact_path)),
            )
        return artifact_id

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT artifact_id, kind, content_type, path, created_at FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def _row_to_job(row: sqlite3.Row | None) -> dict[str, object] | None:
        if row is None:
            return None
        return {
            "job_id": row["job_id"],
            "workflow": row["workflow"],
            "request_hash": row["request_hash"],
            "state": row["state"],
            "progress": float(row["progress"]),
            "payload": json.loads(row["payload_json"]),
            "messages": json.loads(row["messages_json"]),
            "result_ref": row["result_ref"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
