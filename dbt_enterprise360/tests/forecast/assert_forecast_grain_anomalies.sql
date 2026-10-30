{{ config(enabled=var('forecast_models_built', false)) }}
-- PENDING DE: mart_gmv_anomalies (name TBD) not in repo on 2026-10-31; enable with --vars '{forecast_models_built: true}'
select anomaly_date, count(*) from {{ ref('mart_gmv_anomalies') }} group by anomaly_date having count(*) > 1
