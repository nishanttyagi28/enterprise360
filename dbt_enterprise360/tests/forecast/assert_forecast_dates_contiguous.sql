{{ config(enabled=var('forecast_models_built', false)) }}
-- PENDING DE: mart_gmv_forecast (name TBD) not in repo on 2026-10-31; enable with --vars '{forecast_models_built: true}'
-- forecast dates contiguous (monthly assumed; adjust to DE grain)
select forecast_month from (select forecast_month, lag(forecast_month) over (order by forecast_month) p from {{ ref('mart_gmv_forecast') }}) x where p is not null and forecast_month <> p + interval '1 month'
