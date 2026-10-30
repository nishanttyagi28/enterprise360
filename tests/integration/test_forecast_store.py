"""Forecast persistence: one run = one transaction, row counts and latest-run semantics (test DB only)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest

from analytics.forecasting.core import MonthlySeries, add_months, run_forecast
from analytics.forecasting.store import OlistMonthly, write_run
from ingestion.config import Settings
from ingestion.pipeline import apply_ddl, connect

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def conn(test_db_name: str) -> Iterator[psycopg.Connection]:
    if test_db_name in {Settings().pg_db, "enterprise360"}:
        pytest.fail("refusing to write test runs into the main warehouse")
    s = Settings().model_copy(update={"pg_db": test_db_name})
    try:
        psycopg.connect(s.conninfo, connect_timeout=3).close()
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    with connect(s) as c:
        apply_ddl(c, ROOT / "database" / "ddl")
        yield c


def test_write_run_persists_all_parts(conn: psycopg.Connection) -> None:
    months = tuple(add_months(date(2017, 1, 1), i) for i in range(20))
    data = OlistMonthly(
        MonthlySeries("gmv", months, tuple(1000.0 + 50 * i for i in range(20))),
        MonthlySeries("orders", months, tuple(10.0 + i for i in range(20))),
    )
    params = {"horizon": 6, "validation_months": 3, "test_months": 3}
    gmv, orders = run_forecast(data.gmv, **params), run_forecast(data.orders, **params)
    run_id = write_run(conn, data, gmv, orders, params)

    def one(sql: str) -> int:
        row = conn.execute(sql, (run_id,)).fetchone()  # type: ignore[arg-type]
        assert row is not None
        return int(row[0])

    assert one("select count(*) from analytics.forecast_monthly where run_id = %s") == 26
    assert one("select count(*) from analytics.forecast_anomalies where run_id = %s") == 20
    assert (
        one("select count(*) from analytics.forecast_backtest where run_id = %s") >= 10
    )  # cv x 3 models + val/test x (model, baseline)
    assert (
        one(
            "select count(*) from analytics.forecast_monthly where run_id = %s"
            " and split in ('test', 'forecast') and forecast_month <= training_cutoff"
        )
        == 0
    )
