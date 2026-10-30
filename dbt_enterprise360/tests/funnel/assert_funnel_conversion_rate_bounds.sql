{{ config(enabled=var('funnel_models_built', false)) }}
-- DE models committed (bb277c9) and built; funnel_models_built=true by default
select * from {{ ref('mart_funnel_monthly') }} where conversion_rate < 0 or conversion_rate > 1
