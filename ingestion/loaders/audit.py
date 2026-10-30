"""Run audit (``raw._load_audit``): one row per file per run. Also the source of truth for
incremental skipping: a file whose sha256 matches the last *successful* load is not reloaded."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

import psycopg


class LoadStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LoadResult:
    source: str
    batch_id: uuid.UUID
    status: LoadStatus
    rows_loaded: int
    file_sha256: str


class LoadAuditRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def last_success_hash(self, source: str, file_name: str) -> str | None:
        """Per (source, file): multi-file sources skip each unchanged file independently."""
        row = self._conn.execute(
            """select file_sha256 from raw._load_audit
               where source_name = %s and source_file = %s and status = 'success'
               order by finished_at desc limit 1""",
            (source, file_name),
        ).fetchone()
        return None if row is None else str(row[0])

    def start(
        self, batch_id: uuid.UUID, source: str, file_name: str, sha: str, size: int, table: str
    ) -> None:
        # Autonomous from the data transaction: committed immediately so a failed load stays visible.
        self._conn.execute(
            """insert into raw._load_audit
               (batch_id, source_name, source_file, file_sha256, file_bytes, target_table, status)
               values (%s, %s, %s, %s, %s, %s, 'running')""",
            (batch_id, source, file_name, sha, size, table),
        )
        self._conn.commit()

    def finish(
        self, batch_id: uuid.UUID, status: LoadStatus, rows: int = 0, error: str | None = None
    ) -> None:
        self._conn.execute(
            """update raw._load_audit
               set status = %s, rows_loaded = %s, error_message = %s, finished_at = now()
               where batch_id = %s""",
            (status.value, rows, error, batch_id),
        )
        self._conn.commit()
