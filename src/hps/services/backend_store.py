"""SQLite-backed job and artifact persistence for the local backend."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import closing
from pathlib import Path

from hps.io.paths import APP_BACKEND_ARTIFACTS_DIR, APP_BACKEND_DB, ensure_runtime_dirs


def _payload_for_storage(value: object, key: str | None = None) -> object:
    """Retain request metadata without duplicating large base64 uploads in SQLite."""

    if key in {"content_b64", "file_bytes_b64"} and isinstance(value, str):
        return {
            "redacted": True,
            "encoded_size": len(value),
            "sha256": hashlib.sha256(value.encode("ascii")).hexdigest(),
        }
    if isinstance(value, dict):
        return {
            str(item_key): _payload_for_storage(item, str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [_payload_for_storage(item) for item in value]
    return value


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
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            job_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "cache_hit_count" not in job_columns:
                conn.execute(
                    "ALTER TABLE jobs ADD COLUMN cache_hit_count INTEGER NOT NULL DEFAULT 0"
                )
            if "execution_duration_ms" not in job_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN execution_duration_ms REAL")
            artifact_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(artifacts)").fetchall()
            }
            if "size_bytes" not in artifact_columns:
                conn.execute(
                    "ALTER TABLE artifacts ADD COLUMN size_bytes INTEGER NOT NULL DEFAULT 0"
                )

    def create_job(self, *, workflow: str, request_hash: str, payload: dict[str, object]) -> str:
        job_id = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, workflow, request_hash, state, progress, payload_json)
                VALUES (?, ?, ?, 'queued', 0.0, ?)
                """,
                (
                    job_id,
                    workflow,
                    request_hash,
                    json.dumps(_payload_for_storage(payload), sort_keys=True),
                ),
            )
        return job_id

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row)

    def find_completed_job(self, *, workflow: str, request_hash: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE workflow = ? AND request_hash = ? AND state = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (workflow, request_hash),
            ).fetchone()
            if row is None:
                return None
            if row["result_ref"]:
                artifact = conn.execute(
                    "SELECT path FROM artifacts WHERE artifact_id = ?", (row["result_ref"],)
                ).fetchone()
                if artifact is None or not Path(artifact["path"]).is_file():
                    return None
            conn.execute(
                "UPDATE jobs SET cache_hit_count = cache_hit_count + 1 WHERE job_id = ?",
                (row["job_id"],),
            )
        job = self._row_to_job(row)
        if job is not None:
            job["cache_hit"] = True
            job["cache_hit_count"] = int(job["cache_hit_count"]) + 1
        return job

    def update_job(
        self,
        job_id: str,
        *,
        state: str | None = None,
        progress: float | None = None,
        result_ref: str | None = None,
        error: str | None = None,
        execution_duration_ms: float | None = None,
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
                        execution_duration_ms = COALESCE(?, execution_duration_ms),
                        messages_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (
                        state,
                        progress,
                        result_ref,
                        error,
                        execution_duration_ms,
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
                INSERT INTO artifacts (artifact_id, kind, content_type, path, size_bytes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (artifact_id, kind, content_type, str(artifact_path), len(data)),
            )
        return artifact_id

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT artifact_id, kind, content_type, path, size_bytes, created_at FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None or not Path(row["path"]).is_file():
            return None
        return dict(row)

    def recover_stale_jobs(self, *, stale_after_seconds: int = 3_600) -> int:
        """Mark queued/running jobs left behind by a stopped backend as failed."""

        modifier = f"-{max(1, int(stale_after_seconds))} seconds"
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                """
                UPDATE jobs
                SET state = 'failed', progress = 1.0,
                    error = 'Backend restarted before this job completed.',
                    messages_json = json_insert(messages_json, '$[#]',
                        'Recovered stale job after backend restart.'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE state IN ('queued', 'running')
                  AND updated_at < datetime('now', ?)
                """,
                (modifier,),
            )
        return int(cursor.rowcount)

    def prune_artifacts(
        self,
        *,
        max_age_days: int = 30,
        max_total_bytes: int = 2_000_000_000,
        keep_at_least: int = 20,
    ) -> dict[str, int]:
        """Delete old derived artifacts while preserving recent results."""

        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT artifact_id, path, size_bytes,
                       created_at < datetime('now', ?) AS expired
                FROM artifacts ORDER BY created_at DESC, artifact_id DESC
                """,
                (f"-{max(0, int(max_age_days))} days",),
            ).fetchall()

        total_bytes = sum(
            int(row["size_bytes"] or 0) or _safe_file_size(Path(row["path"])) for row in rows
        )
        deleted_count = 0
        deleted_bytes = 0
        artifact_root = self._artifact_dir.resolve()
        for index, row in enumerate(rows):
            size = int(row["size_bytes"] or 0) or _safe_file_size(Path(row["path"]))
            should_delete = index >= max(0, keep_at_least) and (
                bool(row["expired"]) or total_bytes > max(0, max_total_bytes)
            )
            if not should_delete:
                continue
            path = Path(row["path"]).resolve()
            if path.parent == artifact_root and path.is_file():
                path.unlink()
            with closing(self._connect()) as conn, conn:
                conn.execute("DELETE FROM artifacts WHERE artifact_id = ?", (row["artifact_id"],))
                conn.execute(
                    """
                    UPDATE jobs SET state = 'expired', result_ref = NULL,
                        error = 'Cached result expired under the artifact retention policy.',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE result_ref = ?
                    """,
                    (row["artifact_id"],),
                )
            deleted_count += 1
            deleted_bytes += size
            total_bytes -= size
        return {"deleted_count": deleted_count, "deleted_bytes": deleted_bytes}

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
            "cache_hit": False,
            "cache_hit_count": int(row["cache_hit_count"]),
            "execution_duration_ms": (
                float(row["execution_duration_ms"])
                if row["execution_duration_ms"] is not None
                else None
            ),
        }


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
