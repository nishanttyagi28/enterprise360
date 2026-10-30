{{ config(enabled=var('forecast_models_built', false)) }}
-- DE forecast marts committed in 9972c3e
select table_name from information_schema.columns where table_schema = '{{ ref('mart_gmv_anomalies').schema }}' and table_name in ('mart_gmv_anomalies','mart_gmv_forecast') and column_name = 'is_anomaly'
