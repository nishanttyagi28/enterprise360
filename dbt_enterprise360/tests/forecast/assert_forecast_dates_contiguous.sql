{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select forecast_month from (select forecast_month, lag(forecast_month) over (order by forecast_month) p from {{ ref('mart_gmv_forecast') }}) x where p is not null and forecast_month <> (p + interval '1 month')::date
