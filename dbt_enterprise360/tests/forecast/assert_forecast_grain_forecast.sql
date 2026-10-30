{{ config(enabled=var('forecast_models_built', false)) }}
-- DE marts in DB (uncommitted on 2026-10-31); columns verified against marts.mart_gmv_forecast / mart_gmv_anomalies / mart_gmv_forecast_backtest
select forecast_month, count(*) from {{ ref('mart_gmv_forecast') }} group by forecast_month having count(*) > 1
