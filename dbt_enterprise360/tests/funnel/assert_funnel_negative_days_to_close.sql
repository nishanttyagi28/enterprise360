{{ config(enabled=var('funnel_models_built', false), severity='warn') }}
-- PENDING DE: fct_leads/fct_closed_deals not in repo on 2026-10-31; enable with --vars '{funnel_models_built: true}'
-- WARN: negative durations (1 expected from raw: -2 days)
select d.mql_id from {{ ref('fct_closed_deals') }} d join {{ ref('fct_leads') }} l using (mql_id) where d.won_date::date < l.first_contact_date::date
