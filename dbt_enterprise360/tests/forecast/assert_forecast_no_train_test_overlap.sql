{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
-- leakage: validation/test/forecast rows must be after the producing model's training_cutoff; train rows at/before it
select * from {{ ref('mart_gmv_forecast') }} where (split in ('validation','test','forecast') and forecast_month <= training_cutoff) or (split = 'train' and forecast_month > training_cutoff)
