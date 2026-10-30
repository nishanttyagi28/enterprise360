{# Shared date-spine + calendar attributes. Used by core.dim_date (Olist) and uci_core.uci_dim_date
   so both calendars are identical in definition while staying separate tables (no cross-source dim).
   calendar_spine(start, end): one row per day, column date_day (inclusive bounds).
   calendar_columns(alias): standard calendar attribute list for a spine aliased `alias`. #}
{% macro calendar_spine(start_date, end_date) %}
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ start_date ~ "' as date)",
        end_date="cast('" ~ end_date ~ "' as date) + 1"
    ) }}
{% endmacro %}

{% macro calendar_columns(s='s') %}
    {{ date_key(s ~ '.date_day') }}                               as date_key,
    {{ s }}.date_day::date                                        as date_day,
    extract(year from {{ s }}.date_day)::int                      as year,
    extract(quarter from {{ s }}.date_day)::int                   as quarter,
    extract(month from {{ s }}.date_day)::int                     as month,
    to_char({{ s }}.date_day, 'FMMonth')                          as month_name,
    to_char({{ s }}.date_day, 'YYYY-MM')                          as year_month,
    date_trunc('month', {{ s }}.date_day)::date                   as month_start,
    date_trunc('week', {{ s }}.date_day)::date                    as week_start,   -- ISO week (Monday)
    extract(isoyear from {{ s }}.date_day)::int                   as iso_year,
    extract(week from {{ s }}.date_day)::int                      as iso_week,
    extract(isodow from {{ s }}.date_day)::int                    as day_of_week,  -- 1=Mon..7=Sun
    to_char({{ s }}.date_day, 'FMDay')                            as day_name,
    extract(isodow from {{ s }}.date_day) in (6, 7)               as is_weekend
{% endmacro %}

{# Month coverage flags (one definition for every source; README "Complete months"):
   complete = whole calendar month inside [min, max] event date; low volume = events <
   ratio x median of complete months; reporting = complete AND not low volume. #}
{% macro month_coverage(relation, ts_col, where=None, ratio=0.1) %}
with events as (
    select {{ ts_col }} as ts from {{ relation }} {% if where %}where {{ where }}{% endif %}
),
coverage as (select min(ts)::date as first_day, max(ts)::date as last_day from events),
months as (
    select generate_series(date_trunc('month', first_day), date_trunc('month', last_day), interval '1 month')::date
           as month_start
    from coverage
),
monthly as (select date_trunc('month', ts)::date as month_start, count(*) as n from events group by 1),
flagged as (
    select m.month_start,
           coalesce(o.n, 0) as orders,
           m.month_start >= c.first_day
             and (m.month_start + interval '1 month - 1 day')::date <= c.last_day as is_complete_month
    from months m
    cross join coverage c
    left join monthly o on o.month_start = m.month_start
),
threshold as (
    select {{ ratio }} * percentile_cont(0.5) within group (order by orders) as min_orders
    from flagged where is_complete_month
)
select
    f.month_start,
    f.orders,
    f.is_complete_month,
    f.orders < t.min_orders                          as is_low_volume_month,
    f.is_complete_month and f.orders >= t.min_orders as is_reporting_month
from flagged f cross join threshold t
{% endmacro %}
