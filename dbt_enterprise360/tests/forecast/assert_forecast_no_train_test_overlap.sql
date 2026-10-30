{{ config(enabled=var('forecast_models_built', false)) }}
-- PENDING DE: mart_gmv_forecast (name TBD) not in repo on 2026-10-31; enable with --vars '{forecast_models_built: true}'
-- leakage: no test/forecast row may fall inside the training window
select * from {{ ref('mart_gmv_forecast') }} where split in ('test','forecast') and forecast_month <= training_cutoff
