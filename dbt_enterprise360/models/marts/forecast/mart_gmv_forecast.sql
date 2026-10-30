-- Grain: forecast_month (latest run only). Olist monthly GMV (= sum of order-item PRICE only; excludes
-- freight; NOT revenue) and orders: actuals for complete reporting months, model fit/backtest/forecast,
-- last-value naive baseline, 95% conformal intervals (interval_method). split: train (fitted_* = in-sample
-- fit, forecast_* null) | validation (fit on train) | test (holdout, fit on train+validation; never used for
-- selection) | forecast (refit on all usable months). model = selected_model (rolling-origin CV on
-- train+validation; falls back to the baseline when no candidate beats it) - see selection_reason.
-- training_cutoff = last month the producing model saw; validation/test/forecast rows are all after it.
select
    m.forecast_month,
    to_char(m.forecast_month, 'YYYYMMDD')::int  as month_date_key,
    m.split,
    m.training_cutoff,
    m.horizon,
    r.gmv_model                                  as model,
    r.gmv_model                                  as selected_model,
    r.gmv_selection_reason                       as selection_reason,
    'naive_last_value'::text                     as baseline_model,
    m.actual_gmv,
    m.fitted_gmv,
    m.forecast_gmv,
    m.lower_gmv,
    m.upper_gmv,
    m.baseline_gmv,
    m.baseline_lower_gmv,
    m.baseline_upper_gmv,
    r.orders_model,
    r.orders_selection_reason,
    m.actual_orders,
    m.fitted_orders,
    m.forecast_orders,
    m.lower_orders,
    m.upper_orders,
    m.baseline_orders,
    m.interval_level,
    m.interval_method,
    coalesce(a.is_gmv_anomaly, false)            as is_gmv_anomaly,
    coalesce(a.is_orders_anomaly, false)         as is_orders_anomaly,
    m.split = 'forecast'                         as is_forecast,
    m.run_id,
    r.generated_at
from {{ source('analytics', 'forecast_monthly') }} m
inner join {{ ref('int_latest_forecast_run') }} r on r.run_id = m.run_id
left join {{ source('analytics', 'forecast_anomalies') }} a
    on a.run_id = m.run_id and a.anomaly_date = m.forecast_month
