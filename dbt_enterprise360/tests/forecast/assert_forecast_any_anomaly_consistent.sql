{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select anomaly_date from {{ ref('mart_gmv_anomalies') }} where is_any_anomaly is distinct from (is_gmv_anomaly or is_orders_anomaly)
