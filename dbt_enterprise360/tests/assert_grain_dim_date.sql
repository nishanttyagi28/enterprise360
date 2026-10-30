-- grain: one row per (date_day) in dim_date. Returns duplicates.
select date_day, count(*) as n from {{ ref('dim_date') }} group by date_day having count(*) > 1
