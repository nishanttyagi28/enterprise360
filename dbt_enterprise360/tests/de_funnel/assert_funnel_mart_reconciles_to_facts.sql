-- block: the cohort mart must keep every lead and every deal exactly once (no fan-out, no loss).
select * from (
select 'leads' as measure, (select count(*) from {{ ref('fct_leads') }}) as fact_value,
       (select sum(mqls) from {{ ref('mart_funnel_monthly') }}) as mart_value
union all
select 'deals', (select count(*) from {{ ref('fct_closed_deals') }}),
       (select sum(converted_leads_in_cohort) from {{ ref('mart_funnel_monthly') }})
union all
select 'deals_ttc', (select count(*) from {{ ref('fct_closed_deals') }}),
       (select sum(deals) from {{ ref('mart_funnel_time_to_close') }})
) r where fact_value is distinct from mart_value
