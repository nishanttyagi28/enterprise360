-- UCI calendar: separate table (decision 2) built from the same macros as core.dim_date, with UCI's
-- own coverage flags (int_uci__month_coverage; 2011-12 partial). No Olist columns or joins.
with spine as (
    {{ calendar_spine(var('uci_date_spine_start'), var('uci_date_spine_end')) }}
)
select
    {{ calendar_columns('s') }},
    coalesce(f.is_complete_month, false)   as is_complete_month,
    coalesce(f.is_low_volume_month, true)  as is_low_volume_month,
    coalesce(f.is_reporting_month, false)  as is_reporting_month
from spine s
left join {{ ref('int_uci__month_coverage') }} f on f.month_start = date_trunc('month', s.date_day)::date
