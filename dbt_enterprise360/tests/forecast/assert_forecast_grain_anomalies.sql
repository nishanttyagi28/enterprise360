{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select anomaly_date, count(*) from {{ ref('mart_gmv_anomalies') }} group by anomaly_date having count(*) > 1
