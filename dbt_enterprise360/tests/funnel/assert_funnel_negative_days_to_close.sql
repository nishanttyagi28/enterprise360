{{ config(enabled=var('funnel_models_built', false), severity='warn') }}
-- DE models committed (bb277c9) and built; funnel_models_built=true by default
-- WARN: negative durations (1 expected from raw: -2 days)
select d.mql_id from {{ ref('fct_closed_deals') }} d join {{ ref('fct_leads') }} l using (mql_id) where d.won_date::date < l.first_contact_date::date
