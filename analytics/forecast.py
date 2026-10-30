"""``python -m analytics.forecast [--horizon 6] [--validation-months 3] [--test-months 3] [--no-dbt]``

Reads monthly Olist GMV (item price only - not revenue) and orders for complete reporting months, fits
the forecast + baseline, writes one run to analytics.forecast_*, then rebuilds the marts that expose the
latest run (marts.mart_gmv_forecast, mart_gmv_anomalies, mart_gmv_forecast_backtest) unless --no-dbt.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence

from analytics.forecasting.core import run_forecast
from analytics.forecasting.store import read_monthly, write_run
from ingestion.config import Settings, get_settings
from ingestion.log_config import configure_logging, get_logger
from ingestion.pipeline import connect

FORECAST_MARTS = "mart_gmv_forecast mart_gmv_anomalies mart_gmv_forecast_backtest"
log = get_logger(__name__)


def run(
    settings: Settings, *, horizon: int = 6, validation_months: int = 3, test_months: int = 3
) -> uuid.UUID:
    """Fit GMV + orders and persist one run; returns its run_id (marts not rebuilt here)."""
    params = {"horizon": horizon, "validation_months": validation_months, "test_months": test_months}
    with connect(settings) as conn:
        data = read_monthly(conn)
        gmv = run_forecast(data.gmv, **params)
        orders = run_forecast(data.orders, **params)
        run_id = write_run(conn, data, gmv, orders, params)
    log.info(
        "forecast_written",
        run_id=str(run_id),
        months=len(data.gmv.months),
        gmv_model=gmv.model,
        orders_model=orders.model,
        gmv_anomalies=[r.month.isoformat() for r in gmv.rows if r.is_anomaly],
        orders_anomalies=[r.month.isoformat() for r in orders.rows if r.is_anomaly],
    )
    return run_id


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--horizon", type=int, default=6, choices=range(3, 7), metavar="3..6")
    parser.add_argument("--validation-months", type=int, default=3)
    parser.add_argument("--test-months", type=int, default=3)
    parser.add_argument("--no-dbt", action="store_true", help="do not rebuild the forecast marts")
    a = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    run(settings, horizon=a.horizon, validation_months=a.validation_months, test_months=a.test_months)
    if not a.no_dbt:
        from orchestration.dbt_runner import DbtCommandError, run_dbt

        try:
            run_dbt(["build", "--select", *FORECAST_MARTS.split()])
        except DbtCommandError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
