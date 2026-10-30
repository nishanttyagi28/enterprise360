"""Pipeline: for each contract -> describe file -> validate -> skip-if-unchanged -> load -> audit."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from pathlib import Path

import psycopg
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingestion.config import Settings
from ingestion.exceptions import IngestionError
from ingestion.extractors.files import describe_file
from ingestion.loaders.audit import LoadAuditRepository, LoadResult, LoadStatus
from ingestion.loaders.postgres import PostgresLoader
from ingestion.log_config import get_logger
from ingestion.sources.contracts import SourceContract
from ingestion.sources.olist import OLIST_CONTRACTS
from ingestion.sources.uci import UCI_CONTRACTS
from ingestion.validators.contract import validate_header

log = get_logger(__name__)


def connect(settings: Settings) -> psycopg.Connection:
    """Connect with exponential back-off: covers a DB service that is still starting."""

    @retry(
        retry=retry_if_exception_type(psycopg.OperationalError),
        stop=stop_after_attempt(settings.connect_retries),
        wait=wait_exponential(multiplier=1, max=20),
        reraise=True,
    )
    def _connect() -> psycopg.Connection:
        return psycopg.connect(settings.conninfo)

    return _connect()


def apply_ddl(conn: psycopg.Connection, ddl_dir: Path) -> list[str]:
    """Apply database/ddl/*.sql in lexical order. Every script is idempotent (IF NOT EXISTS)."""
    applied: list[str] = []
    for script in sorted(ddl_dir.glob("*.sql")):
        conn.execute(script.read_text(encoding="utf-8"))  # type: ignore[arg-type,unused-ignore]
        applied.append(script.name)
    conn.commit()
    log.info("ddl_applied", scripts=applied)
    return applied


def load_source(
    conn: psycopg.Connection,
    contract: SourceContract,
    source_dir: Path,
    *,
    force: bool = False,
    chunk_bytes: int = 1 << 20,
) -> LoadResult:
    """Load a single-file contract (Olist). Multi-file contracts use :func:`load_contract_files`."""
    return load_file(conn, contract, source_dir / contract.file_name, force=force, chunk_bytes=chunk_bytes)


def load_contract_files(
    conn: psycopg.Connection,
    contract: SourceContract,
    source_dir: Path,
    *,
    force: bool = False,
    chunk_bytes: int = 1 << 20,
) -> list[LoadResult]:
    return [
        load_file(conn, contract, source_dir / name, force=force, chunk_bytes=chunk_bytes)
        for name in contract.file_names
    ]


def load_file(
    conn: psycopg.Connection,
    contract: SourceContract,
    path: Path,
    *,
    force: bool = False,
    chunk_bytes: int = 1 << 20,
) -> LoadResult:
    audit = LoadAuditRepository(conn)
    source = describe_file(path)
    validate_header(contract, source.header)
    batch_id = uuid.uuid4()
    bound = log.bind(source=contract.name, batch_id=str(batch_id), sha256=source.sha256[:12])

    if not force and audit.last_success_hash(contract.name, source.path.name) == source.sha256:
        audit.start(
            batch_id,
            contract.name,
            source.path.name,
            source.sha256,
            source.size_bytes,
            contract.qualified_table,
        )
        audit.finish(batch_id, LoadStatus.SKIPPED)
        bound.info("load_skipped_unchanged")
        return LoadResult(contract.name, batch_id, LoadStatus.SKIPPED, 0, source.sha256)

    audit.start(
        batch_id, contract.name, source.path.name, source.sha256, source.size_bytes, contract.qualified_table
    )
    try:
        rows = PostgresLoader(conn, chunk_bytes).replace_from_file(contract, source, batch_id)
    except Exception as exc:
        conn.rollback()
        audit.finish(batch_id, LoadStatus.FAILED, error=str(exc)[:2000])
        bound.error("load_failed", error=str(exc))
        raise IngestionError(f"{contract.name}: load failed: {exc}") from exc
    audit.finish(batch_id, LoadStatus.SUCCESS, rows=rows)
    bound.info("load_succeeded", rows=rows, bytes=source.size_bytes)
    return LoadResult(contract.name, batch_id, LoadStatus.SUCCESS, rows, source.sha256)


def run_olist(
    settings: Settings,
    *,
    source_dir: Path | None = None,
    only: Sequence[str] | None = None,
    force: bool = False,
) -> list[LoadResult]:
    directory = settings.resolve(source_dir or settings.olist_dir)
    contracts: Iterable[SourceContract] = (
        [c for c in OLIST_CONTRACTS if c.name in set(only)] if only else OLIST_CONTRACTS
    )
    log.info("olist_ingest_started", source_dir=str(directory), force=force)
    with connect(settings) as conn:
        results = [
            load_source(conn, c, directory, force=force, chunk_bytes=settings.copy_chunk_bytes)
            for c in contracts
        ]
    _log_summary("olist_ingest_finished", results)
    return results


def run_uci(settings: Settings, *, source_dir: Path | None = None, force: bool = False) -> list[LoadResult]:
    directory = settings.resolve(source_dir or settings.uci_dir)
    log.info("uci_ingest_started", source_dir=str(directory), force=force)
    with connect(settings) as conn:
        results = [
            r
            for c in UCI_CONTRACTS
            for r in load_contract_files(
                conn, c, directory, force=force, chunk_bytes=settings.copy_chunk_bytes
            )
        ]
    _log_summary("uci_ingest_finished", results)
    return results


def _log_summary(event: str, results: Sequence[LoadResult]) -> None:
    log.info(
        event,
        loaded=sum(r.status is LoadStatus.SUCCESS for r in results),
        skipped=sum(r.status is LoadStatus.SKIPPED for r in results),
        rows=sum(r.rows_loaded for r in results),
    )
