"""COPY-based, idempotent loader.

Strategy = *batch replace keyed by file hash*: Olist files are full snapshots (no change
timestamps, no deletes feed), so the correct idempotent operation is "the raw table equals the
latest file". Per file, in ONE transaction:
  1. COPY the file into a session temp table (all text, positional, quote/newline aware);
  2. replace the raw table contents from the temp table, stamping _ingested_at/_source_file/
     _batch_id and computing _row_hash in-database;
  3. commit -> readers see either the old or the new snapshot, never a partial load.
Re-running with an unchanged file is a no-op (sha256 match in the audit table).

ReplaceScope.FILE (several files -> one table): step 2 deletes only rows whose _source_file is this
file. With track_line_numbers, the temp table has an identity column that COPY fills in file order,
which becomes _source_line_no (1 = first data row).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
from psycopg import sql

from ingestion.extractors.files import UTF8_BOM, SourceFile
from ingestion.loaders.hashing import row_hash_sql
from ingestion.sources.contracts import ReplaceScope, SourceContract


def _iter_chunks(path: Path, chunk_bytes: int) -> Iterator[bytes]:
    # Binary read: bytes reach COPY untouched (no newline translation on Windows, no locale codepage).
    with path.open("rb") as fh:
        first = True
        while chunk := fh.read(chunk_bytes):
            if first and chunk.startswith(UTF8_BOM):
                chunk = chunk[len(UTF8_BOM) :]
            first = False
            yield chunk


class PostgresLoader:
    def __init__(self, conn: psycopg.Connection, chunk_bytes: int = 1 << 20) -> None:
        self._conn = conn
        self._chunk_bytes = chunk_bytes

    def replace_from_file(self, contract: SourceContract, source: SourceFile, batch_id: uuid.UUID) -> int:
        tmp = sql.Identifier(f"_stage_{contract.table}")
        target = sql.Identifier(contract.schema, contract.table)
        cols = sql.SQL(", ").join(sql.Identifier(c) for c in contract.columns)
        with self._conn.transaction(), self._conn.cursor() as cur:
            col_defs: list[sql.Composable] = [
                sql.SQL("{} text").format(sql.Identifier(c)) for c in contract.columns
            ]
            if contract.track_line_numbers:
                col_defs.append(sql.SQL("_source_line_no bigint generated always as identity"))
            cur.execute(
                sql.SQL("create temp table {} ({}) on commit drop").format(tmp, sql.SQL(", ").join(col_defs))
            )
            copy_stmt = sql.SQL(
                "copy {} ({}) from stdin with (format csv, header true, encoding 'UTF8')"
            ).format(tmp, cols)
            with cur.copy(copy_stmt) as copy:
                for chunk in _iter_chunks(source.path, self._chunk_bytes):
                    copy.write(chunk)
            # DELETE (not TRUNCATE): MVCC-safe for concurrent readers; TRUNCATE would take an
            # ACCESS EXCLUSIVE lock.
            if contract.replace_scope is ReplaceScope.FILE:
                cur.execute(
                    sql.SQL("delete from {} where _source_file = %s").format(target),
                    (source.path.name,),
                )
            else:
                cur.execute(sql.SQL("delete from {}").format(target))
            line_col = sql.SQL(", _source_line_no") if contract.track_line_numbers else sql.SQL("")
            cur.execute(
                sql.SQL(
                    """insert into {target} ({cols}{line}, _ingested_at, _source_file, _batch_id,
                           _row_hash)
                       select {cols}{line}, now(), %s, %s, {hash} from {tmp}"""
                ).format(
                    target=target,
                    cols=cols,
                    line=line_col,
                    hash=row_hash_sql(contract.columns),
                    tmp=tmp,
                ),
                (source.path.name, batch_id),
            )
            rows = cur.rowcount
            # Fresh planner stats: after a full replace, stale stats made downstream dbt joins pick
            # nested loops (minutes instead of seconds). ANALYZE is transactional and cheap here.
            cur.execute(sql.SQL("analyze {}").format(target))
            return rows
