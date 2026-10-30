{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select forecast_month, count(*) from {{ ref('mart_gmv_forecast') }} group by forecast_month having count(*) > 1
