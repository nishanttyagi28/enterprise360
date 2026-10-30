{{ config(enabled=var('forecast_models_built', false), severity='warn') }}
-- WARN: selected GMV model does not beat the naive baseline on the test holdout (sMAPE)
select m.split, m.smape_pct model_smape, b.smape_pct baseline_smape from {{ ref('mart_gmv_forecast_backtest') }} m join {{ ref('mart_gmv_forecast_backtest') }} b on b.series=m.series and b.split=m.split and b.model='naive_last_value' where m.series='gmv' and m.is_selected_model and m.split='test' and m.smape_pct >= b.smape_pct
