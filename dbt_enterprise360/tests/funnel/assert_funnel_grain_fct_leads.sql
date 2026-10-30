{{ config(enabled=var('funnel_models_built', false)) }}
-- DE models committed (bb277c9) and built; funnel_models_built=true by default
select mql_id, count(*) from {{ ref('fct_leads') }} group by mql_id having count(*) > 1 or mql_id is null
