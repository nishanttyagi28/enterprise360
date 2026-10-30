{{ config(enabled=var('forecast_models_built', false), severity='warn') }}
-- WARN only when the selected GMV model is NOT the baseline and its test sMAPE >= the baseline's; passes if baseline is selected
select m.model, m.smape_pct as model_smape, b.smape_pct as baseline_smape
from {{ ref('mart_gmv_forecast_backtest') }} m
join {{ ref('mart_gmv_forecast_backtest') }} b
  on b.series = m.series and b.split = m.split and b.model = 'naive_last_value'
where m.series = 'gmv' and m.split = 'test' and m.is_selected_model
  and m.model <> 'naive_last_value' and m.smape_pct >= b.smape_pct
