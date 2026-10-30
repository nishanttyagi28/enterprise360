{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select forecast_month, split from {{ ref('mart_gmv_forecast') }} where (split = 'train' and (fitted_gmv is null or forecast_gmv is not null)) or (split <> 'train' and fitted_gmv is not null)
