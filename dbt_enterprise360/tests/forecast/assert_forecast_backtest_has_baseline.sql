{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
-- every series x split has both the selected model and the naive baseline
select series, split from {{ ref('mart_gmv_forecast_backtest') }} group by 1,2 having count(*) filter (where is_selected_model) <> 1 or count(*) filter (where model = 'naive_last_value') <> 1
