-- Generated calendar spine (not derived from data, so every date exists even with no orders).
-- Shared conformed dimension across all Enterprise360 domains (STTM §7).
-- Olist coverage flags come from int_olist__month_coverage (single definition, see README).
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ var('date_spine_start') ~ "' as date)",
        end_date="cast('" ~ var('date_spine_end') ~ "' as date) + 1"
    ) }}
)
select
    {{ date_key('s.date_day') }}                                   as date_key,
    s.date_day::date                                               as date_day,
    extract(year from s.date_day)::int                             as year,
    extract(quarter from s.date_day)::int                          as quarter,
    extract(month from s.date_day)::int                            as month,
    to_char(s.date_day, 'FMMonth')                                 as month_name,
    to_char(s.date_day, 'YYYY-MM')                                 as year_month,
    date_trunc('month', s.date_day)::date                          as month_start,
    date_trunc('week', s.date_day)::date                           as week_start,   -- ISO week (Monday)
    extract(isoyear from s.date_day)::int                          as iso_year,
    extract(week from s.date_day)::int                             as iso_week,
    extract(isodow from s.date_day)::int                           as day_of_week,  -- 1=Mon..7=Sun
    to_char(s.date_day, 'FMDay')                                   as day_name,
    extract(isodow from s.date_day) in (6, 7)                      as is_weekend,
    -- outside Olist coverage: not complete, not reporting; low-volume (0 orders) = true
    coalesce(f.is_complete_month, false)                         as is_complete_month,
    coalesce(f.is_low_volume_month, true)                        as is_low_volume_month,
    coalesce(f.is_reporting_month, false)                        as is_reporting_month
from spine s
left join {{ ref('int_olist__month_coverage') }} f on f.month_start = date_trunc('month', s.date_day)::date
