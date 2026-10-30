"""Read the monthly series from the warehouse and persist one forecast run (single transaction)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date

import psycopg

from analytics.forecasting.core import INTERVAL_LEVEL, INTERVAL_METHOD, ForecastResult, MonthlySeries

SOURCE_RELATION = "marts.mart_business_overview_monthly"
# Train ONLY on whole, reporting months (excludes 2016 sparse months and the 2018-09/10 tail).
SERIES_SQL = f"""
    select month_start, gmv::float8, orders::float8
    from {SOURCE_RELATION}
    where is_complete_month and is_reporting_month
    order by month_start
"""


MONTHLY_COLS = (
    "run_id",
    "forecast_month",
    "split",
    "training_cutoff",
    "horizon",
    "actual_gmv",
    "fitted_gmv",
    "forecast_gmv",
    "lower_gmv",
    "upper_gmv",
    "baseline_gmv",
    "baseline_lower_gmv",
    "baseline_upper_gmv",
    "actual_orders",
    "fitted_orders",
    "forecast_orders",
    "lower_orders",
    "upper_orders",
    "baseline_orders",
    "baseline_lower_orders",
    "baseline_upper_orders",
    "interval_level",
    "interval_method",
)


@dataclass(frozen=True, slots=True)
class OlistMonthly:
    gmv: MonthlySeries
    orders: MonthlySeries


def read_monthly(conn: psycopg.Connection) -> OlistMonthly:
    rows = conn.execute(SERIES_SQL).fetchall()
    if not rows:
        raise RuntimeError(f"no complete reporting months in {SOURCE_RELATION}; run dbt build first")
    months = tuple(date.fromisoformat(str(r[0])) for r in rows)
    return OlistMonthly(
        MonthlySeries("gmv", months, tuple(float(r[1]) for r in rows)),
        MonthlySeries("orders", months, tuple(float(r[2]) for r in rows)),
    )


def write_run(
    conn: psycopg.Connection,
    data: OlistMonthly,
    gmv: ForecastResult,
    orders: ForecastResult,
    params: dict[str, int],
) -> uuid.UUID:
    run_id = uuid.uuid4()
    months = data.gmv.months
    with conn.transaction():
        conn.execute(
            "insert into analytics.forecast_runs (run_id, source_relation, first_month, last_month, n_months,"
            " gmv_model, orders_model, gmv_selection_reason, orders_selection_reason, params, status)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'success')",
            (
                run_id,
                SOURCE_RELATION,
                months[0],
                months[-1],
                len(months),
                gmv.model,
                orders.model,
                gmv.selection_reason,
                orders.selection_reason,
                json.dumps(params),
            ),
        )
        with conn.cursor() as cur:
            cur.executemany(
                f"insert into analytics.forecast_monthly ({', '.join(MONTHLY_COLS)})"
                f" values ({', '.join(['%s'] * len(MONTHLY_COLS))})",
                [
                    (
                        run_id,
                        g.month,
                        g.split,
                        g.training_cutoff,
                        g.horizon,
                        g.actual,
                        g.fitted,
                        g.forecast,
                        g.lower,
                        g.upper,
                        g.baseline,
                        g.baseline_lower,
                        g.baseline_upper,
                        o.actual,
                        o.fitted,
                        o.forecast,
                        o.lower,
                        o.upper,
                        o.baseline,
                        o.baseline_lower,
                        o.baseline_upper,
                        INTERVAL_LEVEL,
                        None if g.split == "train" else INTERVAL_METHOD,
                    )
                    for g, o in zip(gmv.rows, orders.rows, strict=True)
                ],
            )
            cur.executemany(
                "insert into analytics.forecast_anomalies (run_id, anomaly_date, gmv, expected_gmv,"
                " gmv_robust_z, is_gmv_anomaly, orders, expected_orders, orders_robust_z, is_orders_anomaly)"
                " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        run_id,
                        g.month,
                        g.actual,
                        g.expected,
                        g.robust_z,
                        g.is_anomaly,
                        o.actual,
                        o.expected,
                        o.robust_z,
                        o.is_anomaly,
                    )
                    for g, o in zip(gmv.rows, orders.rows, strict=True)
                    if g.actual is not None
                ],
            )
            cur.executemany(
                "insert into analytics.forecast_backtest (run_id, series, model, split, n_months, mae,"
                " smape_pct, mape_pct, is_selected_model) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        run_id,
                        m.series,
                        m.model,
                        m.split,
                        m.n,
                        m.mae,
                        m.smape,
                        None if m.mape != m.mape else m.mape,
                        m.model == res.model,
                    )
                    for res in (gmv, orders)
                    for m in res.metrics
                ],
            )
    return run_id
