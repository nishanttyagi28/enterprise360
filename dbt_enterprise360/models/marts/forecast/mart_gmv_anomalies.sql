-- Grain: anomaly_date (= month start; latest run only), every evaluated month with its flag.
-- robust_z = |r - median(r)| / (1.4826 * MAD(r)), r = actual - expected; anomaly iff robust_z > 3.5.
-- expected = one-step IN-SAMPLE fit of the selected model with parameters estimated on ALL 20 usable months
-- (naive baseline -> previous month), so it is a descriptive flag, not an out-of-sample test. GMV = item price only (not revenue).
select
    a.anomaly_date,
    to_char(a.anomaly_date, 'YYYYMMDD')::int  as month_date_key,
    a.gmv,
    a.expected_gmv,
    a.gmv - a.expected_gmv                    as gmv_residual,
    a.gmv_robust_z,
    a.is_gmv_anomaly,
    a.orders,
    a.expected_orders,
    a.orders_robust_z,
    a.is_orders_anomaly,
    a.is_gmv_anomaly or a.is_orders_anomaly   as is_any_anomaly,
    3.5::numeric                              as z_threshold,
    r.gmv_model                               as model,
    a.run_id,
    r.generated_at
from {{ source('analytics', 'forecast_anomalies') }} a
inner join {{ ref('int_latest_forecast_run') }} r on r.run_id = a.run_id
