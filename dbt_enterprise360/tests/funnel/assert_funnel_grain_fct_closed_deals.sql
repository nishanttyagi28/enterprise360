{{ config(enabled=var('funnel_models_built', false)) }}
-- PENDING DE: fct_closed_deals not in repo on 2026-10-31; enable with --vars '{funnel_models_built: true}'
select mql_id, count(*) from {{ ref('fct_closed_deals') }} group by mql_id having count(*) > 1 or mql_id is null
