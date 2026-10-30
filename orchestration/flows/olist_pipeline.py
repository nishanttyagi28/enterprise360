"""Prefect flow: init-db -> ingest Olist + ingest UCI (independent tasks) -> dbt deps/freshness/build.

The two ingest tasks are independent: a UCI failure is logged and does not stop Olist ingestion (or vice
versa). One ``dbt build`` then runs over whatever loaded; the flow is marked failed at the end if any
ingest task failed. ``dbt build`` interleaves tests with models in DAG order, so a failing
error-severity test stops downstream models from building on bad data.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from prefect import flow, get_run_logger, task

from ingestion.config import Settings, get_settings
from ingestion.loaders import LoadResult, LoadStatus
from ingestion.log_config import configure_logging
from ingestion.pipeline import apply_ddl, connect, run_olist, run_uci
from orchestration.dbt_runner import run_dbt
from orchestration.env import load_env

Domain = Literal["olist", "uci", "all"]
_RUNNERS: dict[str, Callable[..., Sequence[LoadResult]]] = {"olist": run_olist, "uci": run_uci}


@task(retries=2, retry_delay_seconds=30)
def init_db_task() -> list[str]:
    settings = get_settings()
    with connect(settings) as conn:
        return apply_ddl(conn, settings.resolve(settings.ddl_dir))


def _summarise(results: Sequence[LoadResult]) -> dict[str, int]:
    return {
        "loaded": sum(r.status is LoadStatus.SUCCESS for r in results),
        "skipped": sum(r.status is LoadStatus.SKIPPED for r in results),
        "rows": sum(r.rows_loaded for r in results),
    }


@task(retries=2, retry_delay_seconds=30, task_run_name="ingest-{domain}")
def ingest_task(domain: str, source_dir: Path | None, force: bool) -> dict[str, int]:
    settings: Settings = get_settings()
    summary = _summarise(_RUNNERS[domain](settings, source_dir=source_dir, force=force))
    get_run_logger().info("%s ingestion summary: %s", domain, summary)
    return summary


@task(retries=1, retry_delay_seconds=10)
def dbt_task(*args: str) -> None:
    get_run_logger().info("dbt %s", " ".join(args))
    run_dbt(list(args))


@flow(name="olist-pipeline", log_prints=True)
def olist_pipeline(
    source_dir: Path | None = None,
    force: bool = False,
    full_refresh: bool = False,
    domain: Domain = "all",
    uci_source_dir: Path | None = None,
) -> dict[str, dict[str, int] | str]:
    """``source_dir`` overrides the Olist folder, ``uci_source_dir`` the UCI folder."""
    load_env()
    configure_logging(get_settings().log_level)
    logger = get_run_logger()
    init_db_task()
    domains = ["olist", "uci"] if domain == "all" else [domain]
    dirs = {"olist": source_dir, "uci": uci_source_dir}
    # submit both, then wait: independent, so one failing cannot block the other
    futures = {d: ingest_task.submit(d, dirs[d], force) for d in domains}
    outcome: dict[str, dict[str, int] | str] = {}
    for d, fut in futures.items():
        fut.wait()
        state = fut.state
        if state.is_completed():
            outcome[d] = fut.result()
        else:
            outcome[d] = f"FAILED: {state.message}"
            logger.error("ingest-%s failed; continuing so other domains still build: %s", d, state.message)
    dbt_task("deps")
    dbt_task("source", "freshness")
    dbt_task("build", *(["--full-refresh"] if full_refresh else []))
    failed = [d for d, v in outcome.items() if isinstance(v, str)]
    if failed:
        raise RuntimeError(f"ingestion failed for: {', '.join(failed)} (dbt build ran on the rest)")
    return outcome


if __name__ == "__main__":
    olist_pipeline()
