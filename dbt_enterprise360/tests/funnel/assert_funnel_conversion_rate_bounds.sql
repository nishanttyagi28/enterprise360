{{ config(enabled=var('funnel_models_built', false)) }}
-- PENDING DE: mart_funnel_monthly not in repo on 2026-10-31; enable with --vars '{funnel_models_built: true}'
select * from {{ ref('mart_funnel_monthly') }} where conversion_rate < 0 or conversion_rate > 1
