{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select series, model, split, count(*) from {{ ref('mart_gmv_forecast_backtest') }} group by 1,2,3 having count(*) > 1 or split not in ('cv','validation','test')
