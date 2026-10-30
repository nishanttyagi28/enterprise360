-- SINGLE source of truth for Olist month-coverage flags (used by dim_date and
-- mart_business_overview_monthly; test assert_month_coverage_consistent enforces agreement).
-- Rule definition: macros/calendar.sql month_coverage() (shared with UCI). One row per calendar
-- month between the first and last purchase month (zero-order months kept). `orders` = orders.
{{ month_coverage(ref('stg_olist__orders'), 'purchased_at', ratio=var('olist_low_volume_ratio', 0.1)) }}
