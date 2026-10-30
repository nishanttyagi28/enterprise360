-- SINGLE source of truth for Olist month-coverage flags (used by dim_date and
-- mart_business_overview_monthly; test assert_month_coverage_consistent enforces agreement).
-- Rules (README "Complete months"):
--   is_complete_month  : whole calendar month inside [min, max] order purchase DATE.
--   is_low_volume_month: orders < olist_low_volume_ratio (10%) x median orders of complete months.
--   is_reporting_month : complete AND not low volume (use for trends / MoM growth).
-- One row per calendar month between the first and last purchase month (zero-order months kept).
with coverage as (
    select min(purchased_at)::date as first_day, max(purchased_at)::date as last_day
    from {{ ref('stg_olist__orders') }}
),
months as (
    select generate_series(date_trunc('month', first_day), date_trunc('month', last_day), interval '1 month')::date
           as month_start
    from coverage
),
monthly as (
    select date_trunc('month', purchased_at)::date as month_start, count(*) as orders
    from {{ ref('stg_olist__orders') }} group by 1
),
flagged as (
    select m.month_start,
           coalesce(o.orders, 0) as orders,
           m.month_start >= c.first_day
             and (m.month_start + interval '1 month - 1 day')::date <= c.last_day as is_complete_month
    from months m
    cross join coverage c
    left join monthly o on o.month_start = m.month_start
),
threshold as (
    select {{ var('olist_low_volume_ratio', 0.1) }}
           * percentile_cont(0.5) within group (order by orders) as min_orders
    from flagged where is_complete_month
)
select
    f.month_start,
    f.orders,
    f.is_complete_month,
    f.orders < t.min_orders                          as is_low_volume_month,
    f.is_complete_month and f.orders >= t.min_orders as is_reporting_month
from flagged f cross join threshold t
