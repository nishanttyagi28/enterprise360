{{ config(enabled=var('funnel_models_built', false)) }}
-- mart_funnel_monthly exposes (DE bb277c9) converted_leads_in_cohort, mqls, is_cohort_mature (KPI_FUNNEL_CONVERSION_RATE v1.0.1)
-- maturity window locked at 210 days (p95): mature iff month end + 210 days <= max(won_date)
with mx as (select max(won_date)::date as max_won from {{ ref('fct_closed_deals') }})
select m.month_start, m.is_cohort_mature, m.converted_leads_in_cohort, m.mqls
from {{ ref('mart_funnel_monthly') }} m cross join mx
where m.is_cohort_mature is distinct from
      ((date_trunc('month', m.month_start) + interval '1 month - 1 day')::date + 210 <= mx.max_won)
   or m.converted_leads_in_cohort > m.mqls
