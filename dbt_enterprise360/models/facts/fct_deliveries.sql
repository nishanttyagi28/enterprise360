-- Grain: one row per order (delivery process view of the order). All orders are kept so the
-- denominator is explicit; KPIs use is_otd_eligible (STTM 2.1: status delivered AND customer
-- delivery timestamp present AND not before purchase).
with o as (select * from {{ ref('stg_olist__orders') }})
select
    {{ dbt_utils.generate_surrogate_key(['o.order_id']) }}          as order_sk,
    o.order_id,
    m.customer_sk,
    {{ dbt_utils.generate_surrogate_key(['m.customer_zip_prefix']) }} as geography_sk,
    {{ date_key('o.purchased_at') }}                                as purchase_date_key,
    {{ date_key('o.delivered_customer_at') }}                       as delivered_date_key,
    {{ date_key('o.estimated_delivery_at') }}                       as estimated_delivery_date_key,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.delivered_carrier_at,
    o.delivered_customer_at,
    o.estimated_delivery_at,
    round(extract(epoch from (o.delivered_customer_at - o.purchased_at)) / 86400.0, 2) as delivery_days,      -- KPI_DELIVERY_DAYS
    round(extract(epoch from (o.delivered_carrier_at - o.purchased_at)) / 86400.0, 2)  as days_to_carrier,
    round(extract(epoch from (o.delivered_customer_at - o.delivered_carrier_at)) / 86400.0, 2) as days_in_transit,
    (o.delivered_customer_at::date - o.estimated_delivery_at::date)                     as days_vs_estimate, -- >0 late
    -- date-level comparison per KPI_OTD_RATE definition (estimate is a date at 00:00)
    case when o.delivered_customer_at is not null
         then o.delivered_customer_at::date <= o.estimated_delivery_at::date end        as is_on_time,
    (o.order_status = 'delivered' and o.delivered_customer_at is not null
        and o.delivered_customer_at >= o.purchased_at)                                  as is_otd_eligible,
    (o.order_status = 'delivered' and o.delivered_customer_at is null)                  as dq_missing_delivery_ts,
    coalesce(o.delivered_customer_at < o.purchased_at, false)                           as dq_delivered_before_purchase
from o
left join {{ ref('int_olist__customer_order_map') }} m on m.customer_id = o.customer_id
