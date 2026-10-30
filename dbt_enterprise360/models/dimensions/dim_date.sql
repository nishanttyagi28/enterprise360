-- Generated calendar spine (not derived from data, so every date exists even with no orders).
-- Olist calendar. Spine + attributes from macros/calendar.sql (shared definition with uci_dim_date).
-- Olist coverage flags come from int_olist__month_coverage (single definition, see README).
with spine as (
    {{ calendar_spine(var('date_spine_start'), var('date_spine_end')) }}
)
select
    {{ calendar_columns('s') }},
    -- outside Olist coverage: not complete, not reporting; low-volume (0 orders) = true
    coalesce(f.is_complete_month, false)                         as is_complete_month,
    coalesce(f.is_low_volume_month, true)                        as is_low_volume_month,
    coalesce(f.is_reporting_month, false)                        as is_reporting_month
from spine s
left join {{ ref('int_olist__month_coverage') }} f on f.month_start = date_trunc('month', s.date_day)::date
