"""Prefect flow: ingest Olist -> dbt source freshness -> dbt build (models + tests + snapshot).

``dbt build`` interleaves tests with models in DAG order, so a failing error-severity test stops
downstream models from building on bad data (better than run-then-test).
"""

from __future__ import annotations

from pathlib import Path

from prefect import flow, get_run_logger, task

from ingestion.config import get_settings
from ingestion.loaders import LoadStatus
from ingestion.log_config import configure_logging
from ingestion.pipeline import apply_ddl, connect, run_olist
from orchestration.dbt_runner import run_dbt
from orchestration.env import load_env


@task(retries=2, retry_delay_seconds=30)
def init_db_task() -> list[str]:
    settings = get_settings()
    with connect(settings) as conn:
        return apply_ddl(conn, settings.resolve(settings.ddl_dir))


@task(retries=2, retry_delay_seconds=30)
def ingest_task(source_dir: Path | None, force: bool) -> dict[str, int]:
    logger = get_run_logger()
    results = run_olist(get_settings(), source_dir=source_dir, force=force)
    summary = {
        "loaded": sum(r.status is LoadStatus.SUCCESS for r in results),
        "skipped": sum(r.status is LoadStatus.SKIPPED for r in results),
        "rows": sum(r.rows_loaded for r in results),
    }
    logger.info("ingestion summary: %s", summary)
    return summary


@task(retries=1, retry_delay_seconds=10)
def dbt_task(*args: str) -> None:
    get_run_logger().info("dbt %s", " ".join(args))
    run_dbt(list(args))


@flow(name="olist-pipeline", log_prints=True)
def olist_pipeline(source_dir: Path | None = None, force: bool = False, full_refresh: bool = False) -> None:
    load_env()
    configure_logging(get_settings().log_level)
    init_db_task()
    ingest_task(source_dir, force)
    dbt_task("deps")
    dbt_task("source", "freshness")
    dbt_task("build", *(["--full-refresh"] if full_refresh else []))


if __name__ == "__main__":
    olist_pipeline()
