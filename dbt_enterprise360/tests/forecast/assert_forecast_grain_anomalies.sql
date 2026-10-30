{{ config(enabled=var('forecast_models_built', false)) }}
-- DE marts in DB (uncommitted on 2026-10-31); columns verified against marts.mart_gmv_forecast / mart_gmv_anomalies / mart_gmv_forecast_backtest
select anomaly_date, count(*) from {{ ref('mart_gmv_anomalies') }} group by anomaly_date having count(*) > 1
