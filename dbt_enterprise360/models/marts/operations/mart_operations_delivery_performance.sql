-- Grain: purchase month x customer state. Only KPI-eligible deliveries enter the OTD/lead-time
-- measures; counts of excluded/DQ rows are kept for transparency.
select
    date_trunc('month', d.purchased_at)::date                                  as month_start,
    g.state                                                                    as customer_state,
    count(*)                                                                   as orders,
    count(*) filter (where d.is_otd_eligible)                                  as delivered_orders,
    count(*) filter (where d.is_otd_eligible and d.is_on_time)                 as on_time_orders,
    round((count(*) filter (where d.is_otd_eligible and d.is_on_time))::numeric
          / nullif(count(*) filter (where d.is_otd_eligible), 0), 4)          as otd_rate,          -- KPI_OTD_RATE
    round(avg(d.delivery_days) filter (where d.is_otd_eligible), 2)            as avg_delivery_days, -- KPI_DELIVERY_DAYS
    round(avg(d.days_to_carrier) filter (where d.is_otd_eligible), 2)          as avg_days_to_carrier,
    round(avg(d.days_vs_estimate) filter (where d.is_otd_eligible and not d.is_on_time), 2) as avg_days_late_when_late,
    round(avg(extract(epoch from (d.approved_at - d.purchased_at)) / 3600.0), 2) as avg_approval_hours, -- KPI_APPROVAL_HOURS
    count(*) filter (where d.dq_missing_delivery_ts)                           as dq_missing_delivery_ts,
    count(*) filter (where d.dq_delivered_before_purchase)                     as dq_delivered_before_purchase
from {{ ref('fct_deliveries') }} d
left join {{ ref('dim_geography') }} g on g.geography_sk = d.geography_sk
group by 1, 2
