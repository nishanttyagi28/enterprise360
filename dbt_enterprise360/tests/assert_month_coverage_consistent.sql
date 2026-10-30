-- is_partial_month (mart) must be exactly NOT is_complete_month (dim_date) for every month,
-- and the Olist edge months must be flagged (2016-09 first partial month, 2018-10 last).
with d as (select distinct month_start, is_complete_month from {{ ref('dim_date') }})
select m.month_start, m.is_partial_month, d.is_complete_month
from {{ ref('mart_business_overview_monthly') }} m
left join d on d.month_start = m.month_start
where d.is_complete_month is null or m.is_partial_month <> (not d.is_complete_month)
union all
select c.month_start, null, c.is_complete_month
from {{ ref('int_olist__month_coverage') }} c
where c.month_start in ((select min(month_start) from {{ ref('int_olist__month_coverage') }}),
                        (select max(month_start) from {{ ref('int_olist__month_coverage') }}))
  and c.is_complete_month
