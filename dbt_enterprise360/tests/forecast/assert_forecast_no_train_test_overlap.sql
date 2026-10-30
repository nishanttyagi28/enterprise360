{{ config(enabled=var('forecast_models_built', false)) }}
-- DE marts in DB (uncommitted on 2026-10-31); columns verified against marts.mart_gmv_forecast / mart_gmv_anomalies / mart_gmv_forecast_backtest
-- leakage: validation/test/forecast rows must be after the producing model's training_cutoff; train rows at/before it
select * from {{ ref('mart_gmv_forecast') }} where (split in ('validation','test','forecast') and forecast_month <= training_cutoff) or (split = 'train' and forecast_month > training_cutoff)
