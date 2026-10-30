{{ config(enabled=var('funnel_models_built', false), severity='warn') }}
-- PENDING DE: fct_leads/fct_closed_deals not in repo on 2026-10-31; enable with --vars '{funnel_models_built: true}'
-- WARN: rows returned = closed deals with no matching MQL (0 expected from raw)
select d.mql_id from {{ ref('fct_closed_deals') }} d left join {{ ref('fct_leads') }} l using (mql_id) where l.mql_id is null
