{{ config(enabled=var('funnel_models_built', false), severity='warn') }}
-- DE models committed (bb277c9) and built; funnel_models_built=true by default
-- WARN: rows returned = closed deals with no matching MQL (0 expected from raw)
select d.mql_id from {{ ref('fct_closed_deals') }} d left join {{ ref('fct_leads') }} l using (mql_id) where l.mql_id is null
