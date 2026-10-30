{{ config(enabled=var('forecast_models_built', false)) }}
-- DE marts in DB (uncommitted on 2026-10-31); columns verified against marts.mart_gmv_forecast / mart_gmv_anomalies / mart_gmv_forecast_backtest
select forecast_month from (select forecast_month, lag(forecast_month) over (order by forecast_month) p from {{ ref('mart_gmv_forecast') }}) x where p is not null and forecast_month <> (p + interval '1 month')::date
