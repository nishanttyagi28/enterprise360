-- Grain: first_contact_month x origin (lead COHORT). A deal is attributed to its lead's first-contact month,
-- never to its won month. conversion_rate = converted_leads_in_cohort / mqls; it is a ratio: Power BI must
-- use sum(converted_leads_in_cohort) / sum(mqls) for any rollup.
-- Duration stats use days_to_close = won_date::date - first_contact_date, EXCLUDING negative durations
-- (source anomaly, flagged by a warn test). median_days_to_close is per-row display only (not rollable);
-- avg can be rebuilt from sum_days_to_close / deals_with_valid_duration.
-- is_cohort_mature: (cohort month end + 210 days) <= max(won_date); 210 days = locked p95 days-to-close
-- (KPI dictionary), so immature cohorts still have conversions to come.
-- is_deal_window_complete: false for cohorts that start before the first month with any won deal in the
-- source (closed deals only exist from 2017-12): those cohorts are LEFT-censored (earlier wins missing).
with bounds as (
    select max(won_date)::date                     as max_won_date,
           date_trunc('month', min(won_date))::date as first_won_month
    from {{ ref('fct_closed_deals') }}
)
select
    f.first_contact_month                                                        as month_start,
    to_char(f.first_contact_month, 'YYYYMMDD')::int                              as month_date_key,
    f.origin_sk,
    f.origin,
    count(*)                                                                     as mqls,
    count(*) filter (where f.is_closed)                                          as converted_leads_in_cohort,
    round(count(*) filter (where f.is_closed)::numeric / count(*), 4)            as conversion_rate,
    count(*) filter (where f.is_closed and f.days_to_close between 0 and 90)     as converted_within_90d,
    percentile_cont(0.5) within group (order by f.days_to_close)
        filter (where f.is_closed and f.days_to_close >= 0)                      as median_days_to_close,
    round(avg(f.days_to_close) filter (where f.is_closed and f.days_to_close >= 0), 1)
                                                                                 as avg_days_to_close,
    coalesce(sum(f.days_to_close) filter (where f.is_closed and f.days_to_close >= 0), 0)
                                                                                 as sum_days_to_close,
    count(*) filter (where f.is_closed and f.days_to_close >= 0)                 as deals_with_valid_duration,
    (f.first_contact_month + interval '1 month' - interval '1 day')::date + 210 <= b.max_won_date
                                                                                 as is_cohort_mature,
    f.first_contact_month >= b.first_won_month                                   as is_deal_window_complete
from {{ ref('fct_leads') }} f
cross join bounds b
group by 1, 2, 3, 4, b.max_won_date, b.first_won_month
